import { redirect } from "next/navigation";
import { fetchCurrentUser } from "@/lib/api-client";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import type { RoleName, UserMeResponse } from "@/types/identity";

export interface VerifiedSessionContext {
  user: UserMeResponse;
  accessToken: string;
}

export async function requireAuthenticatedUser(options?: {
  allowedRoles?: RoleName[];
  currentPath?: string;
}): Promise<VerifiedSessionContext> {
  const supabase = await createSupabaseServerClient();
  if (!supabase) {
    redirect("/login?error=supabase_unconfigured");
  }

  const {
    data: { user: authUser },
  } = await supabase.auth.getUser();

  if (!authUser) {
    const nextParam = options?.currentPath
      ? `?next=${encodeURIComponent(options.currentPath)}`
      : "";
    redirect(`/login${nextParam}`);
  }

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    redirect("/login");
  }

  const user = await fetchCurrentUser(session.access_token);

  if (options?.allowedRoles && options.allowedRoles.length > 0) {
    const authorized = user.roles.some((role) =>
      options.allowedRoles?.includes(role),
    );
    if (!authorized) {
      redirect("/student?error=forbidden");
    }
  }

  return {
    user,
    accessToken: session.access_token,
  };
}
