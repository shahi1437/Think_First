import {
  fetchAdminAuditLogs,
  fetchAdminTeacherManagement,
  fetchAdminUsers,
} from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";
import { AuditAccessClient } from "@/features/admin/audit-access-client";
import { TeacherManagementSection } from "@/features/admin/teacher-management-section";

export const dynamic = "force-dynamic";

export default async function AdminAuditPage() {
  const { accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["admin"],
    currentPath: "/admin/audit",
  });

  const [usersRes, logsRes, teacherMgmt] = await Promise.all([
    fetchAdminUsers(accessToken, 50),
    fetchAdminAuditLogs(accessToken, { limit: 50 }),
    fetchAdminTeacherManagement(accessToken).catch(() => null),
  ]);

  return (
    <div className="space-y-6">
      <TeacherManagementSection
        accessToken={accessToken}
        initialActiveTeachers={teacherMgmt?.active_teachers ?? []}
        initialInvitations={teacherMgmt?.invitations ?? []}
      />
      <AuditAccessClient
        accessToken={accessToken}
        initialUsers={usersRes.items}
        initialLogs={logsRes.items}
      />
    </div>
  );
}
