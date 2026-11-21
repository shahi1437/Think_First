import { KeyRound } from "lucide-react";
import { AuthPortalShell } from "@/components/auth-portal-shell";
import { ResetPasswordForm } from "@/features/auth/reset-password-form";
import type { RoleName } from "@/types/identity";

export const dynamic = "force-dynamic";

interface ResetPasswordPageProps {
  searchParams: Promise<{ portal?: string }>;
}

function parsePortal(raw?: string): RoleName | undefined {
  if (raw === "student" || raw === "teacher" || raw === "admin") {
    return raw;
  }
  return undefined;
}

export default async function ResetPasswordPage({
  searchParams,
}: ResetPasswordPageProps) {
  const params = await searchParams;
  const portal = parsePortal(params.portal);

  return (
    <AuthPortalShell
      badge="Set New Password"
      title="Choose a new password"
      subtitle="Create a strong password for your Think_First account, then sign in through your authorized portal."
      icon={KeyRound}
      accent="indigo"
      footerLinks={[
        { href: "/login/student", label: "Student Login" },
        { href: "/login/teacher", label: "Teacher Login" },
        { href: "/login/admin", label: "Admin Login" },
      ]}
    >
      <ResetPasswordForm portal={portal} />
    </AuthPortalShell>
  );
}
