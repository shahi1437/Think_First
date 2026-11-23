import { Users } from "lucide-react";
import { AuthPortalShell } from "@/components/auth-portal-shell";
import { AcceptTeacherInviteClient } from "@/features/auth/accept-teacher-invite-client";

export const dynamic = "force-dynamic";

interface AcceptTeacherInvitePageProps {
  searchParams: Promise<{ token?: string }>;
}

export default async function AcceptTeacherInvitePage({
  searchParams,
}: AcceptTeacherInvitePageProps) {
  const params = await searchParams;

  return (
    <AuthPortalShell
      badge="Teacher Invitation"
      title="Accept Teacher Invitation"
      subtitle="Verify your administrator-issued invitation to activate Teacher portal access on your Think_First account."
      icon={Users}
      accent="indigo"
      footerLinks={[
        { href: "/login/teacher", label: "Teacher Login" },
        { href: "/login/student", label: "Student Login" },
        { href: "/", label: "Back to Home" },
      ]}
    >
      <AcceptTeacherInviteClient token={params.token} />
    </AuthPortalShell>
  );
}
