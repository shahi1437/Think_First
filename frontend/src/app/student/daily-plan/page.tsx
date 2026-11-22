import { LanguageSelector } from "@/components/language-selector";
import { DailyPlanClient } from "@/features/growth/daily-plan-client";
import {
  fetchDailyPlanWorkspace,
  fetchLanguageProgressOverview,
} from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function StudentDailyPlanPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/daily-plan",
  });

  const [languageOverview, workspace] = await Promise.all([
    fetchLanguageProgressOverview(accessToken),
    fetchDailyPlanWorkspace(accessToken),
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
      <DailyPlanClient
        key={languageOverview.active_language_slug}
        accessToken={accessToken}
        initialWorkspace={workspace}
        initialLanguage={explanationLang}
      />
    </div>
  );
}
