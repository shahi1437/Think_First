import { redirect } from "next/navigation";
import { cache } from "react";
import { ApiClientError, fetchCurrentUser } from "@/lib/api-client";
import {
  resolveDefaultPortalPath,
  resolvePortalLoginPath,
} from "@/lib/auth/roles";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import type { RoleName, UserMeResponse } from "@/types/identity";

export interface VerifiedSessionContext {
  user: UserMeResponse;
  accessToken: string;
}

type SessionResolution =
  | { status: "ok"; context: VerifiedSessionContext }
  | { status: "unconfigured" }
  | { status: "unauthenticated" };

// Deduplicate Supabase + FastAPI identity verification within a single RSC request
// (prevents duplicate round-trips across layout.tsx and page.tsx without caching across requests/users).
const resolveVerifiedSession = cache(async (): Promise<SessionResolution> => {
  const supabase = await createSupabaseServerClient();
  if (!supabase) {
    return { status: "unconfigured" };
  }

  const {
    data: { user: authUser },
  } = await supabase.auth.getUser();

  if (!authUser) {
    return { status: "unauthenticated" };
  }

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    return { status: "unauthenticated" };
  }

  try {
    const user = await fetchCurrentUser(session.access_token);
    return {
      status: "ok",
      context: { user, accessToken: session.access_token },
    };
  } catch (err) {
    if (err instanceof ApiClientError && err.status === 401) {
      return { status: "unauthenticated" };
    }
    throw err;
  }
});

export async function requireAuthenticatedUser(options?: {
  allowedRoles?: RoleName[];
  currentPath?: string;
}): Promise<VerifiedSessionContext> {
  const loginPath = resolvePortalLoginPath(options?.currentPath);
  const nextQuery = options?.currentPath
    ? `?next=${encodeURIComponent(options.currentPath)}`
    : "";

  const resolved = await resolveVerifiedSession();
  if (resolved.status === "unconfigured") {
    redirect(`${loginPath}?error=supabase_unconfigured`);
  }
  if (resolved.status === "unauthenticated") {
    redirect(`${loginPath}${nextQuery}`);
  }

  const { user, accessToken } = resolved.context;

  if (options?.allowedRoles && options.allowedRoles.length > 0) {
    const authorized = user.roles.some((role) =>
      options.allowedRoles?.includes(role),
    );
    if (!authorized) {
      redirect(`${resolveDefaultPortalPath(user.roles)}?error=forbidden`);
    }
  }

  return {
    user,
    accessToken,
  };
}
