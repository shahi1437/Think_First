import { TeacherDashboardClient } from "@/features/teacher/teacher-dashboard-client";
import { fetchTeacherDashboard } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function TeacherDashboardPage({
  searchParams,
}: {
  searchParams?: Promise<{ error?: string }>;
}) {
  const params = searchParams ? await searchParams : {};
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["teacher", "admin"],
    currentPath: "/teacher",
  });

  const dashboard = await fetchTeacherDashboard(accessToken);

  return (
    <div className="space-y-4">
      {params.error === "forbidden" ? (
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          Access denied for the requested Admin-only route: your current account
          holds{" "}
          <span className="font-mono font-semibold">
            {user.roles.join(", ")}
          </span>{" "}
          permissions.
        </div>
      ) : null}
      <TeacherDashboardClient
        teacherName={user.full_name || user.email}
        initialDashboard={dashboard}
        initialLanguage={
          user.preferences?.preferred_explanation_language ?? "en"
        }
      />
    </div>
  );
}
