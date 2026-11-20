import { redirect } from "next/navigation";
import { DiagnosticWorkspace } from "@/features/learning/diagnostic-workspace";
import { fetchMyDiagnosticSessions } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export default async function StudentDiagnosticPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/diagnostic",
  });

  if (!user.onboarding_completed) {
    redirect("/student/onboarding");
  }

  const history = await fetchMyDiagnosticSessions(accessToken);

  return (
    <DiagnosticWorkspace
      accessToken={accessToken}
      initialHistory={history}
      initialLanguage={user.preferences?.preferred_explanation_language ?? "en"}
    />
  );
}
