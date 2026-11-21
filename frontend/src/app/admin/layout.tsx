import type { ReactNode } from "react";
import { AppShell } from "@/components/app-shell";
import { ServiceUnavailableState } from "@/components/service-unavailable-state";
import { BackendUnavailableError } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function AdminLayout({
  children,
}: {
  children: ReactNode;
}) {
  let user;
  try {
    ({ user } = await requireAuthenticatedUser({
      allowedRoles: ["admin"],
      currentPath: "/admin",
    }));
  } catch (err) {
    if (err instanceof BackendUnavailableError) {
      return (
        <main className="min-h-screen bg-slate-50">
          <ServiceUnavailableState title="Admin Console Temporarily Unavailable" />
        </main>
      );
    }
    throw err;
  }

  return (
    <AppShell
      user={user}
      activeRole="admin"
      navLinks={[
        { href: "/admin", label: "Overview" },
        { href: "/admin/problems", label: "Problem Studio" },
        { href: "/admin/curriculum", label: "Curriculum & Lessons" },
        { href: "/admin/diagnostics", label: "Diagnostics & RAG" },
        { href: "/admin/audit", label: "Users & Audit" },
      ]}
    >
      {children}
    </AppShell>
  );
}
