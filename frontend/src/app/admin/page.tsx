import Link from "next/link";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export default async function AdminDashboardPage() {
  const { user } = await requireAuthenticatedUser({
    allowedRoles: ["admin"],
    currentPath: "/admin",
  });

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
          Authorized Admin Studio
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">
          Platform Administration — {user.full_name || user.email}
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Your database-backed <code className="font-mono text-xs">admin</code>{" "}
          role is verified. Manage authoring, automated Judge0 validation,
          review approvals, and publishing inside Problem Studio.
        </p>
        <div className="mt-5">
          <Link
            href="/admin/problems"
            className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-indigo-700"
          >
            Open Problem Studio
          </Link>
        </div>
      </div>
    </div>
  );
}
