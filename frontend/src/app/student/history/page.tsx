import { LearningHistoryClient } from "@/features/growth/learning-history-client";
import { fetchLearningHistory } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function StudentLearningHistoryPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/history",
  });

  const history = await fetchLearningHistory(accessToken, { limit: 50 });

  return (
    <LearningHistoryClient
      accessToken={accessToken}
      initialHistory={history}
      initialLanguage={
        user.preferences?.preferred_explanation_language ?? "en"
      }
    />
  );
}
