import { redirect } from "next/navigation";
import { LearningDashboardClient } from "@/features/learning/learning-dashboard-client";
import { fetchLearningDashboard } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export default async function StudentDashboardPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student",
  });

  if (!user.onboarding_completed) {
    redirect("/student/onboarding");
  }

  const dashboard = await fetchLearningDashboard(accessToken);

  return (
    <LearningDashboardClient
      accessToken={accessToken}
      studentName={user.full_name || user.email}
      initialDashboard={dashboard}
      initialLanguage={user.preferences?.preferred_explanation_language ?? "en"}
    />
  );
}
