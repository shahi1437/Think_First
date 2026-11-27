import type { ReactNode } from "react";
import { AppShell } from "@/components/app-shell";
import { ServiceUnavailableState } from "@/components/service-unavailable-state";
import { BackendUnavailableError } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function StudentLayout({
  children,
}: {
  children: ReactNode;
}) {
  let user;
  let accessToken;
  try {
    ({ user, accessToken } = await requireAuthenticatedUser({
      allowedRoles: ["student", "teacher", "admin"],
      currentPath: "/student",
    }));
  } catch (err) {
    if (err instanceof BackendUnavailableError) {
      return (
        <main className="min-h-screen bg-[#f7f8fa]">
          <ServiceUnavailableState />
        </main>
      );
    }
    throw err;
  }

  return (
    <AppShell
      user={user}
      accessToken={accessToken}
      activeRole="student"
      navLinks={[
        { href: "/student", label: "Dashboard" },
        { href: "/student/classes", label: "Classes" },
        { href: "/student/assignments", label: "Assignments" },
        { href: "/student/daily-plan", label: "Daily Plan" },
        { href: "/student/lessons", label: "Lessons" },
        { href: "/student/diagnostic", label: "Diagnostic" },
        { href: "/student/problems", label: "Problem Bank" },
        { href: "/student/dna", label: "Learning DNA" },
        { href: "/student/retention", label: "Retention" },
        { href: "/student/history", label: "History" },
        { href: "/student/settings", label: "Settings" },
      ]}
    >
      {children}
    </AppShell>
  );
}
