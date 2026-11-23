import { notFound } from "next/navigation";
import { CodingWorkspace } from "@/features/workspace/coding-workspace";
import {
  ApiClientError,
  fetchExecutionStatus,
  fetchMySubmissions,
  fetchProblemDetail,
  fetchTransferChallenge,
  fetchWorkspaceRevisions,
} from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

interface ProblemWorkspacePageProps {
  params: Promise<{ id: string }>;
  searchParams?: Promise<{ tab?: string }>;
}

export const dynamic = "force-dynamic";

export default async function ProblemWorkspacePage({
  params,
  searchParams,
}: ProblemWorkspacePageProps) {
  const { id } = await params;
  const query = searchParams ? await searchParams : {};
  const { user, accessToken } = await requireAuthenticatedUser({
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

  const [submissionsRes, revisions, transferChallenge, executionStatus] =
    await Promise.all([
      fetchMySubmissions(accessToken, problem.problem_id),
      fetchWorkspaceRevisions(accessToken, problem.version_id),
      fetchTransferChallenge(accessToken, problem.problem_id).catch(() => null),
      fetchExecutionStatus(accessToken).catch(() => null),
    ]);

  const initialTab =
    query.tab === "verify" || query.tab === "mentor" ? query.tab : undefined;

  return (
    <CodingWorkspace
      accessToken={accessToken}
      problem={problem}
      initialSubmissions={submissionsRes.items}
      initialRevisions={revisions}
      initialTransferChallenge={transferChallenge}
      initialExecutionStatus={executionStatus}
      preferredLanguageSlug={user.preferences?.active_language_slug ?? "python"}
      initialBottomTab={initialTab}
    />
  );
}
