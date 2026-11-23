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
  | { status: "unauthenticated"; reason?: "session_expired" };

// Deduplicate identity verification within a single RSC request
// (prevents duplicate round-trips across layout.tsx and page.tsx without caching across requests/users).
// Note: proxy.ts already refreshes Supabase Auth cookies via supabase.auth.getUser(), and
// fetchCurrentUser() cryptographically verifies the Supabase JWT signature/audience/expiry via JWKS
// and enforces DB-backed roles on FastAPI — avoiding a redundant second Supabase HTTP round-trip here.
const resolveVerifiedSession = cache(async (): Promise<SessionResolution> => {
  const supabase = await createSupabaseServerClient();
  if (!supabase) {
    return { status: "unconfigured" };
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
      // Attempt one clean refresh-token rotation before treating the session as expired
      try {
        const { data: refreshed, error: refreshError } =
          await supabase.auth.refreshSession();
        const refreshedToken = refreshed.session?.access_token;
        if (!refreshError && refreshedToken) {
          const user = await fetchCurrentUser(refreshedToken);
          return {
            status: "ok",
            context: { user, accessToken: refreshedToken },
          };
        }
      } catch {
        // Fall through to clean session_expired redirect
      }
      return { status: "unauthenticated", reason: "session_expired" };
    }
    throw err;
  }
});

export async function requireAuthenticatedUser(options?: {
  allowedRoles?: RoleName[];
  currentPath?: string;
}): Promise<VerifiedSessionContext> {
  const loginPath = resolvePortalLoginPath(options?.currentPath);

  const buildLoginRedirect = (errorCode?: string) => {
    const params = new URLSearchParams();
    if (options?.currentPath) {
      params.set("next", options.currentPath);
    }
    if (errorCode) {
      params.set("error", errorCode);
    }
    const qs = params.toString();
    return qs ? `${loginPath}?${qs}` : loginPath;
  };

  const resolved = await resolveVerifiedSession();
  if (resolved.status === "unconfigured") {
    redirect(buildLoginRedirect("supabase_unconfigured"));
  }
  if (resolved.status === "unauthenticated") {
    redirect(buildLoginRedirect(resolved.reason));
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
