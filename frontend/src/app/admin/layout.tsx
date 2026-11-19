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
        { href: "/admin", label: "Admin Dashboard" },
        { href: "/admin/problems", label: "Problem Studio" },
        { href: "/student", label: "Student View" },
      ]}
    >
      {children}
    </AppShell>
  );
}
