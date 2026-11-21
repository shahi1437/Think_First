import { Users } from "lucide-react";
import { redirect } from "next/navigation";
import { AuthPortalShell } from "@/components/auth-portal-shell";
import { LoginForm } from "@/features/auth/login-form";
import { fetchCurrentUser } from "@/lib/api-client";
import {
  isAuthorizedForLoginPortal,
  resolvePostLoginRedirect,
} from "@/lib/auth/roles";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

interface TeacherLoginPageProps {
  searchParams: Promise<{ next?: string; error?: string }>;
}

function mapLoginError(errorCode?: string): string | undefined {
  if (errorCode === "auth_callback_failed") {
    return "Authentication link verification failed or expired. Please sign in again.";
  }
  if (errorCode === "supabase_unconfigured") {
    return "Authentication service is not configured for this environment yet.";
  }
  return undefined;
}

export default async function TeacherLoginPage({
  searchParams,
}: TeacherLoginPageProps) {
  const params = await searchParams;
  let initialError = mapLoginError(params.error);

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
          if (isAuthorizedForLoginPortal(user.roles, "teacher")) {
            redirectTarget = resolvePostLoginRedirect(
              user.roles,
              params.next ?? "/teacher",
            );
          } else {
            initialError =
              "Your current signed-in session does not have Teacher access. Sign in with an authorized Teacher account.";
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
      badge="Teacher Portal"
      title="Teacher Login"
      subtitle="Sign in to manage classes, publish coding assignments, and review student submissions."
      icon={Users}
      accent="indigo"
      footerLinks={[
        { href: "/login/student", label: "Student Login" },
        { href: "/login/admin", label: "Admin Login" },
        { href: "/", label: "Back to Home" },
      ]}
    >
      <LoginForm
        portal="teacher"
        nextPath={params.next}
        initialError={initialError}
      />
    </AuthPortalShell>
  );
}
