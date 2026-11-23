import { GraduationCap } from "lucide-react";
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

interface StudentLoginPageProps {
  searchParams: Promise<{ next?: string; error?: string }>;
}

export default async function StudentLoginPage({
  searchParams,
}: StudentLoginPageProps) {
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
          if (isAuthorizedForLoginPortal(user.roles, "student")) {
            redirectTarget = resolvePostLoginRedirect(
              user.roles,
              params.next ?? "/student",
            );
          } else {
            initialSuggestedPortal = getPrimaryRole(user.roles);
            initialError =
              "You are currently signed in with a non-Student portal role. Sign out first or open your authorized portal.";
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
      badge="Student Portal"
      title="Student Login"
      subtitle="Sign in to continue your Python lessons, practice problems, and class assignments."
      icon={GraduationCap}
      accent="teal"
      footerLinks={[
        { href: "/login/teacher", label: "Teacher Login" },
        { href: "/login/admin", label: "Admin Login" },
        { href: "/", label: "Back to Home" },
      ]}
    >
      <LoginForm
        portal="student"
        nextPath={params.next}
        initialError={initialError}
        initialSuggestedPortal={initialSuggestedPortal}
      />
    </AuthPortalShell>
  );
}
