import { redirect } from "next/navigation";
import { LearningDashboardClient } from "@/features/learning/learning-dashboard-client";
import {
  fetchDailyPlanWorkspace,
  fetchLearningDashboard,
  fetchLearningDnaProfile,
  fetchRetentionOverview,
} from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export default async function StudentDashboardPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student",
  });

  if (!user.onboarding_completed) {
    redirect("/student/onboarding");
  }

  const [dashboard, dnaProfile, dailyPlanWorkspace, retentionOverview] =
    await Promise.all([
      fetchLearningDashboard(accessToken),
      fetchLearningDnaProfile(accessToken),
      fetchDailyPlanWorkspace(accessToken),
      fetchRetentionOverview(accessToken),
    ]);

  return (
    <LearningDashboardClient
      accessToken={accessToken}
      studentName={user.full_name || user.email}
      initialDashboard={dashboard}
      initialLanguage={user.preferences?.preferred_explanation_language ?? "en"}
      dnaSummary={{
        verifiedCount: dnaProfile.dimensions.filter(
          (d) => d.evidence_band === "verified",
        ).length,
        totalDimensions: dnaProfile.dimensions.length,
        strengths: dnaProfile.strengths,
      }}
      dailyPlanSummary={{
        completedTasks: dailyPlanWorkspace.active_plan.completed_tasks,
        totalTasks: dailyPlanWorkspace.active_plan.total_tasks,
        availableMinutes: dailyPlanWorkspace.active_plan.available_minutes,
        versionNumber: dailyPlanWorkspace.active_plan.version_number,
      }}
      retentionSummary={{
        dueCount: retentionOverview.due_count,
        scheduledCount: retentionOverview.schedules.length,
        retainedSkillsCount: retentionOverview.retained_skills_count,
      }}
    />
  );
}
