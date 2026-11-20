import { StudentClassesClient } from "@/features/student-classroom/student-classes-client";
import { fetchStudentClasses } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function StudentClassesPage() {
  const { accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/classes",
  });

  const classes = await fetchStudentClasses(accessToken);

  return (
    <StudentClassesClient
      accessToken={accessToken}
      initialClasses={classes}
    />
  );
}
