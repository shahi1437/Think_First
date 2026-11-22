import { LanguageSelector } from "@/components/language-selector";
import { RetentionClient } from "@/features/growth/retention-client";
import {
  fetchLanguageProgressOverview,
  fetchRetentionOverview,
} from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function StudentRetentionPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/retention",
  });

  const [languageOverview, overview] = await Promise.all([
    fetchLanguageProgressOverview(accessToken),
    fetchRetentionOverview(accessToken),
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
      <RetentionClient
        key={languageOverview.active_language_slug}
        accessToken={accessToken}
        initialOverview={overview}
        initialLanguage={explanationLang}
      />
    </div>
  );
}
