import type { ReactNode } from "react";
import { AppShell } from "@/components/app-shell";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function AdminLayout({
  children,
}: {
  children: ReactNode;
}) {
  const { user } = await requireAuthenticatedUser({
    allowedRoles: ["admin"],
    currentPath: "/admin",
  });

  return (
    <AppShell
      user={user}
      activeRole="admin"
      navLinks={[
        { href: "/admin", label: "Overview" },
        { href: "/admin/problems", label: "Problem Studio" },
        { href: "/admin/curriculum", label: "Curriculum & Lessons" },
        { href: "/admin/diagnostics", label: "Diagnostics & RAG" },
        { href: "/admin/audit", label: "Audit & Access" },
        { href: "/student", label: "Student View" },
      ]}
    >
      {children}
    </AppShell>
  );
}
