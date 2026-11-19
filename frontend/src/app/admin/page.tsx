import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export default async function AdminDashboardPage() {
  const { user } = await requireAuthenticatedUser({
    allowedRoles: ["admin"],
    currentPath: "/admin",
  });

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
        Authorized Admin Studio
      </p>
      <h1 className="mt-1 text-2xl font-bold text-slate-900">
        Platform Administration — {user.full_name || user.email}
      </h1>
      <p className="mt-2 text-sm text-slate-600">
        Your database-backed <code className="font-mono text-xs">admin</code>{" "}
        role is verified. Audited role assignment endpoints (
        <code className="font-mono text-xs">/api/v1/admin/users</code>) are
        active; Problem Studio and content governance workflows arrive in Phases
        3 and 8.
      </p>
    </div>
  );
}
