import { fetchAdminAuditLogs, fetchAdminUsers } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";
import { AuditAccessClient } from "@/features/admin/audit-access-client";

export const dynamic = "force-dynamic";

export default async function AdminAuditPage() {
  const { accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["admin"],
    currentPath: "/admin/audit",
  });

  const [usersRes, logsRes] = await Promise.all([
    fetchAdminUsers(accessToken, 50),
    fetchAdminAuditLogs(accessToken, { limit: 50 }),
  ]);

  return (
    <AuditAccessClient
      accessToken={accessToken}
      initialUsers={usersRes.items}
      initialLogs={logsRes.items}
    />
  );
}
