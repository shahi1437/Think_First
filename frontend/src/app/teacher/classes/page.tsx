import { TeacherClassesClient } from "@/features/teacher/teacher-classes-client";
import { fetchTeacherClasses } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function TeacherClassesPage() {
  const { accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["teacher", "admin"],
    currentPath: "/teacher/classes",
  });

  const classes = await fetchTeacherClasses(accessToken);

  return (
    <TeacherClassesClient accessToken={accessToken} initialClasses={classes} />
  );
}
