import { redirect } from "next/navigation";
import { LanguageSelector } from "@/components/language-selector";
import { DiagnosticWorkspace } from "@/features/learning/diagnostic-workspace";
import {
  fetchLanguageProgressOverview,
  fetchMyDiagnosticSessions,
} from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";
import type { AssessmentMode } from "@/types/learning";

export const dynamic = "force-dynamic";

export default async function StudentDiagnosticPage({
  searchParams,
}: {
  searchParams?: Promise<{ mode?: string; entry?: string }>;
}) {
  const params = searchParams ? await searchParams : {};
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/diagnostic",
  });

  if (!user.onboarding_completed) {
    redirect("/student/onboarding");
  }

  const [languageOverview, history] = await Promise.all([
    fetchLanguageProgressOverview(accessToken),
    fetchMyDiagnosticSessions(accessToken),
  ]);
  const explanationLang =
    user.preferences?.preferred_explanation_language ?? "en";
  const initialMode: AssessmentMode =
    params.mode === "readiness" ? "readiness" : "full";
  const fromOnboarding = params.entry === "onboarding";

  return (
    <div className="tf-animate-enter space-y-6">
      <LanguageSelector
        key={languageOverview.active_language_slug}
        accessToken={accessToken}
        initialOverview={languageOverview}
        explanationLanguage={explanationLang}
        compact
      />
      <DiagnosticWorkspace
        key={languageOverview.active_language_slug}
        accessToken={accessToken}
        initialHistory={history}
        activeLanguageSlug={languageOverview.active_language_slug}
        initialLanguage={explanationLang}
        recommendedMode={initialMode}
        fromOnboarding={fromOnboarding}
      />
    </div>
  );
}
