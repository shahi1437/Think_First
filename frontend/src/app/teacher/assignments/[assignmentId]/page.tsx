import { TeacherAssignmentReviewClient } from "@/features/teacher/teacher-assignment-review-client";
import { fetchTeacherAssignmentDetail } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function TeacherAssignmentDetailPage({
  params,
}: {
  params: Promise<{ assignmentId: string }>;
}) {
  const { assignmentId } = await params;
  const { accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["teacher", "admin"],
    currentPath: `/teacher/assignments/${assignmentId}`,
  });

  const detail = await fetchTeacherAssignmentDetail(accessToken, assignmentId);

  return (
    <TeacherAssignmentReviewClient
      accessToken={accessToken}
      initialDetail={detail}
    />
  );
}
