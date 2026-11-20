import { StudentAssignmentsClient } from "@/features/student-classroom/student-assignments-client";
import { fetchStudentAssignments } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function StudentAssignmentsPage() {
  const { accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/assignments",
  });

  const assignments = await fetchStudentAssignments(accessToken, "all");

  return (
    <StudentAssignmentsClient
      accessToken={accessToken}
      initialAssignments={assignments}
    />
  );
}
