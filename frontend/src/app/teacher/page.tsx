import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export default async function TeacherDashboardPage() {
  const { user } = await requireAuthenticatedUser({
    allowedRoles: ["teacher", "admin"],
    currentPath: "/teacher",
  });

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wider text-teal-700">
        Authorized Teacher Portal
      </p>
      <h1 className="mt-1 text-2xl font-bold text-slate-900">
        Welcome, {user.full_name || user.email}
      </h1>
      <p className="mt-2 text-sm text-slate-600">
        Your database-backed <code className="font-mono text-xs">teacher</code>{" "}
        role is verified. Course management, assignment builder, student
        submission review, and class analytics will be enabled in Phase 7.
      </p>
    </div>
  );
}
