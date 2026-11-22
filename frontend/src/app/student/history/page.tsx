import { LanguageSelector } from "@/components/language-selector";
import { LearningHistoryClient } from "@/features/growth/learning-history-client";
import {
  fetchLanguageProgressOverview,
  fetchLearningHistory,
} from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function StudentLearningHistoryPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/history",
  });

  const [languageOverview, history] = await Promise.all([
    fetchLanguageProgressOverview(accessToken),
    fetchLearningHistory(accessToken, { limit: 50 }),
  ]);
  const explanationLang =
    user.preferences?.preferred_explanation_language ?? "en";

  return (
    <div className="space-y-6">
      <LanguageSelector
        key={languageOverview.active_language_slug}
        accessToken={accessToken}
        initialOverview={languageOverview}
        explanationLanguage={explanationLang}
        compact
      />
      <LearningHistoryClient
        key={languageOverview.active_language_slug}
        accessToken={accessToken}
        initialHistory={history}
        initialLanguage={explanationLang}
      />
    </div>
  );
}
