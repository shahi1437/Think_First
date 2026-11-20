import { notFound } from "next/navigation";
import { CodingWorkspace } from "@/features/workspace/coding-workspace";
import {
  ApiClientError,
  fetchMySubmissions,
  fetchProblemDetail,
  fetchTransferChallenge,
  fetchWorkspaceRevisions,
} from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

interface ProblemWorkspacePageProps {
  params: Promise<{ id: string }>;
}

export default async function ProblemWorkspacePage({
  params,
}: ProblemWorkspacePageProps) {
  const { id } = await params;
  const { accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: `/student/problems/${id}`,
  });

  let problem;
  try {
    problem = await fetchProblemDetail(accessToken, id);
  } catch (err) {
    if (err instanceof ApiClientError && err.status === 404) {
      notFound();
    }
    throw err;
  }

  const [submissionsRes, revisions, transferChallenge] = await Promise.all([
    fetchMySubmissions(accessToken, problem.problem_id),
    fetchWorkspaceRevisions(accessToken, problem.version_id),
    fetchTransferChallenge(accessToken, problem.problem_id).catch(() => null),
  ]);

  return (
    <CodingWorkspace
      accessToken={accessToken}
      problem={problem}
      initialSubmissions={submissionsRes.items}
      initialRevisions={revisions}
      initialTransferChallenge={transferChallenge}
    />
  );
}
