import { TeacherAssignmentsClient } from "@/features/teacher/teacher-assignments-client";
import {
  fetchProblems,
  fetchTeacherAssignments,
  fetchTeacherClasses,
} from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function TeacherAssignmentsPage() {
  const { accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["teacher", "admin"],
    currentPath: "/teacher/assignments",
  });

  const [classes, assignments, problemsPage] = await Promise.all([
    fetchTeacherClasses(accessToken),
    fetchTeacherAssignments(accessToken),
    fetchProblems(accessToken, { limit: 40 }),
  ]);

  return (
    <TeacherAssignmentsClient
      accessToken={accessToken}
      initialClasses={classes}
      initialAssignments={assignments}
      publishedProblems={problemsPage.items}
    />
  );
}
