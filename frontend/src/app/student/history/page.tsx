import { LanguageSelector } from "@/components/language-selector";
import { LearningHistoryClient } from "@/features/growth/learning-history-client";
import {
  fetchDebuggingTimeline,
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

  const [languageOverview, history, debuggingTimeline] = await Promise.all([
    fetchLanguageProgressOverview(accessToken),
    fetchLearningHistory(accessToken, { limit: 50 }),
    fetchDebuggingTimeline(accessToken, { limit: 15 }).catch(() => null),
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
        initialDebuggingTimeline={debuggingTimeline}
        initialLanguage={explanationLang}
      />
    </div>
  );
}
