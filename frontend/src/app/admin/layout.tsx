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
  let accessToken;
  try {
    ({ user, accessToken } = await requireAuthenticatedUser({
      allowedRoles: ["admin"],
      currentPath: "/admin",
    }));
  } catch (err) {
    if (err instanceof BackendUnavailableError) {
      return (
        <main className="min-h-screen bg-[#f7f8fa]">
          <ServiceUnavailableState title="Admin Console Temporarily Unavailable" />
        </main>
      );
    }
    throw err;
  }

  return (
    <AppShell
      user={user}
      accessToken={accessToken}
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
