import { ProblemBankClient } from "@/features/problems/problem-bank-client";
import { fetchProblems } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function StudentProblemsPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/problems",
  });

  const initialData = await fetchProblems(accessToken, { limit: 30 });

  return (
    <ProblemBankClient
      accessToken={accessToken}
      initialProblems={initialData.items}
      initialTotal={initialData.total}
      activeLanguageSlug={user.preferences?.active_language_slug ?? "python"}
    />
  );
}
