import { DailyPlanClient } from "@/features/growth/daily-plan-client";
import { fetchDailyPlanWorkspace } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function StudentDailyPlanPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/daily-plan",
  });

  const workspace = await fetchDailyPlanWorkspace(accessToken);

  return (
    <DailyPlanClient
      accessToken={accessToken}
      initialWorkspace={workspace}
      initialLanguage={
        user.preferences?.preferred_explanation_language ?? "en"
      }
    />
  );
}
