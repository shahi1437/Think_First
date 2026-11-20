import type { ReactNode } from "react";
import { AppShell } from "@/components/app-shell";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function TeacherLayout({
  children,
}: {
  children: ReactNode;
}) {
  const { user } = await requireAuthenticatedUser({
    allowedRoles: ["teacher", "admin"],
    currentPath: "/teacher",
  });

  return (
    <AppShell
      user={user}
      activeRole="teacher"
      navLinks={[
        { href: "/teacher", label: "Dashboard" },
        { href: "/teacher/classes", label: "My Classes" },
        { href: "/teacher/assignments", label: "Assignments" },
        { href: "/student", label: "Student View" },
      ]}
    >
      {children}
    </AppShell>
  );
}
