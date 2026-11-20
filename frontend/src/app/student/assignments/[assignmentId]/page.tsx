import { StudentAssignmentDetailClient } from "@/features/student-classroom/student-assignment-detail-client";
import {
  fetchProblemDetail,
  fetchStudentAssignmentDetail,
} from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";
import type { StudentProblemDetail } from "@/types/problems";

export const dynamic = "force-dynamic";

export default async function StudentAssignmentDetailPage({
  params,
}: {
  params: Promise<{ assignmentId: string }>;
}) {
  const { assignmentId } = await params;
  const { accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: `/student/assignments/${assignmentId}`,
  });

  const detail = await fetchStudentAssignmentDetail(accessToken, assignmentId);
  const problemDetails = await Promise.all(
    detail.problems.map((p) => fetchProblemDetail(accessToken, p.problem_id)),
  );
  const problemsById: Record<string, StudentProblemDetail> = Object.fromEntries(
    problemDetails.map((pd) => [pd.problem_id, pd]),
  );

  return (
    <StudentAssignmentDetailClient
      accessToken={accessToken}
      initialDetail={detail}
      problemsById={problemsById}
    />
  );
}
