import { ShieldCheck } from "lucide-react";
import { redirect } from "next/navigation";
import { AuthPortalShell } from "@/components/auth-portal-shell";
import { LoginForm } from "@/features/auth/login-form";
import { fetchCurrentUser } from "@/lib/api-client";
import { mapAuthPageError } from "@/lib/auth/auth-helpers";
import {
  getPrimaryRole,
  isAuthorizedForLoginPortal,
  resolvePostLoginRedirect,
} from "@/lib/auth/roles";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import type { RoleName } from "@/types/identity";

export const dynamic = "force-dynamic";

interface AdminLoginPageProps {
  searchParams: Promise<{ next?: string; error?: string }>;
}

export default async function AdminLoginPage({
  searchParams,
}: AdminLoginPageProps) {
  const params = await searchParams;
  let initialError = mapAuthPageError(params.error);
  let initialSuggestedPortal: RoleName | undefined;

  const supabase = await createSupabaseServerClient();
  if (supabase) {
    const {
      data: { user: authUser },
    } = await supabase.auth.getUser();
    if (authUser) {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session?.access_token) {
        let redirectTarget: string | null = null;
        try {
          const user = await fetchCurrentUser(session.access_token);
          if (isAuthorizedForLoginPortal(user.roles, "admin")) {
            redirectTarget = resolvePostLoginRedirect(
              user.roles,
              params.next ?? "/admin",
            );
          } else {
            initialSuggestedPortal = getPrimaryRole(user.roles);
            initialError =
              "Your current signed-in session does not have Admin access. Sign in with an authorized Admin account.";
          }
        } catch {
          initialError =
            initialError ??
            "Unable to verify your current session right now. Please sign in below.";
        }
        if (redirectTarget) {
          redirect(redirectTarget);
        }
      }
    }
  }

  return (
    <AuthPortalShell
      badge="Admin Security Portal"
      title="Admin Login"
      subtitle="Authorized administrator access for user roles, course oversight, curriculum, and system health."
      icon={ShieldCheck}
      accent="slate"
      footerLinks={[
        { href: "/login/student", label: "Student Login" },
        { href: "/login/teacher", label: "Teacher Login" },
        { href: "/", label: "Back to Home" },
      ]}
    >
      <LoginForm
        portal="admin"
        nextPath={params.next}
        initialError={initialError}
        initialSuggestedPortal={initialSuggestedPortal}
      />
    </AuthPortalShell>
  );
}
