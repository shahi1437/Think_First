import { KeyRound } from "lucide-react";
import { AuthPortalShell } from "@/components/auth-portal-shell";
import { ForgotPasswordForm } from "@/features/auth/forgot-password-form";
import { parsePortalParam } from "@/lib/auth/auth-helpers";

interface ForgotPasswordPageProps {
  searchParams: Promise<{ portal?: string }>;
}

export default async function ForgotPasswordPage({
  searchParams,
}: ForgotPasswordPageProps) {
  const params = await searchParams;
  const portal = parsePortalParam(params.portal);

  return (
    <AuthPortalShell
      badge="Account Recovery"
      title="Reset your password"
      subtitle="Enter your registered email address and we will send you a secure password recovery link."
      icon={KeyRound}
      accent="indigo"
      footerLinks={[
        { href: "/login/student", label: "Student Login" },
        { href: "/login/teacher", label: "Teacher Login" },
        { href: "/login/admin", label: "Admin Login" },
      ]}
    >
      <ForgotPasswordForm portal={portal} />
    </AuthPortalShell>
  );
}
