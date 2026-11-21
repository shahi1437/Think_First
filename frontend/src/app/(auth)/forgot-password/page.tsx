import { KeyRound } from "lucide-react";
import { AuthPortalShell } from "@/components/auth-portal-shell";
import { ForgotPasswordForm } from "@/features/auth/forgot-password-form";
import type { RoleName } from "@/types/identity";

interface ForgotPasswordPageProps {
  searchParams: Promise<{ portal?: string }>;
}

function parsePortal(raw?: string): RoleName | undefined {
  if (raw === "student" || raw === "teacher" || raw === "admin") {
    return raw;
  }
  return undefined;
}

export default async function ForgotPasswordPage({
  searchParams,
}: ForgotPasswordPageProps) {
  const params = await searchParams;
  const portal = parsePortal(params.portal);

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
