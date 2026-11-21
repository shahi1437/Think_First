import { SystemStatusCard } from "@/components/system-status-card";
import {
  fetchAdminOperationsHealth,
  fetchAdminOverview,
} from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";
import { AdminDashboardClient } from "@/features/admin/admin-dashboard-client";

export const dynamic = "force-dynamic";

export default async function AdminDashboardPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["admin"],
    currentPath: "/admin",
  });

  const [overview, operationsHealth] = await Promise.all([
    fetchAdminOverview(accessToken),
    fetchAdminOperationsHealth(accessToken).catch(() => null),
  ]);

  return (
    <div className="space-y-6">
      <AdminDashboardClient
        adminName={user.full_name || user.email}
        overview={overview}
        operationsHealth={operationsHealth}
      />
      <SystemStatusCard />
    </div>
  );
}
