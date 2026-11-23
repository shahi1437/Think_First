import { KeyRound } from "lucide-react";
import { AuthPortalShell } from "@/components/auth-portal-shell";
import { ResetPasswordForm } from "@/features/auth/reset-password-form";
import { parsePortalParam } from "@/lib/auth/auth-helpers";

export const dynamic = "force-dynamic";

interface ResetPasswordPageProps {
  searchParams: Promise<{ portal?: string; error?: string }>;
}

export default async function ResetPasswordPage({
  searchParams,
}: ResetPasswordPageProps) {
  const params = await searchParams;
  const portal = parsePortalParam(params.portal);

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
      <ResetPasswordForm portal={portal} initialErrorCode={params.error} />
    </AuthPortalShell>
  );
}
