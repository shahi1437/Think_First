import type { ReactNode } from "react";
import { AppShell } from "@/components/app-shell";
import { ServiceUnavailableState } from "@/components/service-unavailable-state";
import { BackendUnavailableError } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function TeacherLayout({
  children,
}: {
  children: ReactNode;
}) {
  let user;
  let accessToken;
  try {
    ({ user, accessToken } = await requireAuthenticatedUser({
      allowedRoles: ["teacher", "admin"],
      currentPath: "/teacher",
    }));
  } catch (err) {
    if (err instanceof BackendUnavailableError) {
      return (
        <main className="min-h-screen bg-[#f7f8fa]">
          <ServiceUnavailableState title="Teacher Portal Temporarily Unavailable" />
        </main>
      );
    }
    throw err;
  }

  return (
    <AppShell
      user={user}
      accessToken={accessToken}
      activeRole="teacher"
      navLinks={[
        { href: "/teacher", label: "Dashboard" },
        { href: "/teacher/classes", label: "My Classes" },
        { href: "/teacher/assignments", label: "Assignments" },
      ]}
    >
      {children}
    </AppShell>
  );
}
