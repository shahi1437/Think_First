import { TeacherDashboardClient } from "@/features/teacher/teacher-dashboard-client";
import { fetchTeacherDashboard } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function TeacherDashboardPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["teacher", "admin"],
    currentPath: "/teacher",
  });

  const dashboard = await fetchTeacherDashboard(accessToken);

  return (
    <TeacherDashboardClient
      teacherName={user.full_name || user.email}
      initialDashboard={dashboard}
      initialLanguage={
        user.preferences?.preferred_explanation_language ?? "en"
      }
    />
  );
}
