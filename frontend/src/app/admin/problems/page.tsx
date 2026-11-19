import { AdminProblemStudio } from "@/features/admin/problem-studio";
import { fetchAdminProblems } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export default async function AdminProblemsPage() {
  const { accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["admin"],
    currentPath: "/admin/problems",
  });

  const initial = await fetchAdminProblems(accessToken);

  return (
    <AdminProblemStudio
      accessToken={accessToken}
      initialProblems={initial.items}
    />
  );
}
