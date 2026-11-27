import { redirect } from "next/navigation";
import { LearningDashboardClient } from "@/features/learning/learning-dashboard-client";
import {
  fetchDailyPlanWorkspace,
  fetchDebuggingTimeline,
  fetchLanguageProgressOverview,
  fetchLearningDashboard,
  fetchLearningDnaProfile,
  fetchRetentionOverview,
  fetchStudentAssignments,
  fetchStudentClasses,
  fetchStudentDashboardBundle,
  fetchVerifiedLearningProgress,
} from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function StudentDashboardPage({
  searchParams,
}: {
  searchParams?: Promise<{ error?: string }>;
}) {
  const params = searchParams ? await searchParams : {};
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student",
  });

  if (!user.onboarding_completed) {
    redirect("/student/onboarding");
  }

  const [bundle, verifiedProgress, debuggingTimeline] = await Promise.all([
    fetchStudentDashboardBundle(accessToken).catch(async () => {
      const [
        languageOverview,
        dashboard,
        dnaProfile,
        dailyPlanWorkspace,
        retentionOverview,
        enrolledClasses,
        studentAssignments,
      ] = await Promise.all([
        fetchLanguageProgressOverview(accessToken),
        fetchLearningDashboard(accessToken),
        fetchLearningDnaProfile(accessToken),
        fetchDailyPlanWorkspace(accessToken),
        fetchRetentionOverview(accessToken),
        fetchStudentClasses(accessToken).catch(() => []),
        fetchStudentAssignments(accessToken).catch(() => []),
      ]);
      return {
        language_overview: languageOverview,
        dashboard,
        dna_profile: dnaProfile,
        daily_plan_workspace: dailyPlanWorkspace,
        retention_overview: retentionOverview,
        enrolled_classes: enrolledClasses,
        student_assignments: studentAssignments,
      };
    }),
    fetchVerifiedLearningProgress(accessToken).catch(() => null),
    fetchDebuggingTimeline(accessToken, { limit: 4 }).catch(() => null),
  ]);

  const {
    language_overview: languageOverview,
    dashboard,
    dna_profile: dnaProfile,
    daily_plan_workspace: dailyPlanWorkspace,
    retention_overview: retentionOverview,
    enrolled_classes: enrolledClasses,
    student_assignments: studentAssignments,
  } = bundle;

  return (
    <div className="space-y-4">
      {params.error === "forbidden" ? (
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          Access denied for the requested Teacher/Admin portal: your current
          account only holds{" "}
          <span className="font-mono font-semibold">
            {user.roles.join(", ")}
          </span>{" "}
          permissions. An authorized Admin must grant Teacher or Admin access
          first.
        </div>
      ) : null}
      <LearningDashboardClient
        key={dashboard.language_slug}
        accessToken={accessToken}
        studentName={user.full_name || user.email}
        initialDashboard={dashboard}
        languageOverview={languageOverview}
        initialLanguage={
          user.preferences?.preferred_explanation_language ?? "en"
        }
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
        verifiedProgress={verifiedProgress}
        debuggingTimeline={debuggingTimeline}
        classroomSummary={{
          enrolledCount: enrolledClasses.filter(
            (c) => c.membership_status === "active",
          ).length,
          pendingAssignmentsCount: studentAssignments.filter(
            (a) =>
              a.workflow_status !== "graded" &&
              a.workflow_status !== "submitted",
          ).length,
          totalAssignmentsCount: studentAssignments.length,
          recentClasses: enrolledClasses.slice(0, 3).map((c) => ({
            courseId: c.course_id,
            code: c.code,
            title: c.title,
            status: c.membership_status,
          })),
        }}
      />
    </div>
  );
}
