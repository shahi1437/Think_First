import { TeacherClassDetailClient } from "@/features/teacher/teacher-class-detail-client";
import { fetchTeacherClassDetail } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function TeacherClassDetailPage({
  params,
}: {
  params: Promise<{ courseId: string }>;
}) {
  const { courseId } = await params;
  const { accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["teacher", "admin"],
    currentPath: `/teacher/classes/${courseId}`,
  });

  const detail = await fetchTeacherClassDetail(accessToken, courseId);

  return (
    <TeacherClassDetailClient
      accessToken={accessToken}
      initialDetail={detail}
    />
  );
}
