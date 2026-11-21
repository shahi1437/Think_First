import { GraduationCap } from "lucide-react";
import { AuthPortalShell } from "@/components/auth-portal-shell";
import { RegisterForm } from "@/features/auth/register-form";

export default function RegisterPage() {
  return (
    <AuthPortalShell
      badge="Student Registration"
      title="Create your student account"
      subtitle="Join Think_First to learn Python, practice coding problems, and track your programming growth."
      icon={GraduationCap}
      accent="teal"
      footerLinks={[
        { href: "/login/student", label: "Student Login" },
        { href: "/login/teacher", label: "Teacher Login" },
        { href: "/", label: "Back to Home" },
      ]}
    >
      <RegisterForm />
    </AuthPortalShell>
  );
}
