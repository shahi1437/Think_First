import type { ReactNode } from "react";
import { AppShell } from "@/components/app-shell";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function StudentLayout({
  children,
}: {
  children: ReactNode;
}) {
  const { user } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student",
  });

  return (
    <AppShell
      user={user}
      activeRole="student"
      navLinks={[
        { href: "/student", label: "Dashboard" },
        { href: "/student/lessons", label: "Lessons" },
        { href: "/student/diagnostic", label: "Diagnostic" },
        { href: "/student/problems", label: "Problem Bank" },
        { href: "/student/onboarding", label: "Onboarding" },
        { href: "/student/settings", label: "Settings" },
      ]}
    >
      {children}
    </AppShell>
  );
}
