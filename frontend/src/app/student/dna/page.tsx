import { LanguageSelector } from "@/components/language-selector";
import { LearningDnaClient } from "@/features/growth/learning-dna-client";
import {
  fetchLanguageProgressOverview,
  fetchLearningDnaProfile,
} from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function StudentLearningDnaPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/dna",
  });

  const [languageOverview, profile] = await Promise.all([
    fetchLanguageProgressOverview(accessToken),
    fetchLearningDnaProfile(accessToken),
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
      <LearningDnaClient
        key={languageOverview.active_language_slug}
        accessToken={accessToken}
        initialProfile={profile}
        initialLanguage={explanationLang}
      />
    </div>
  );
}
