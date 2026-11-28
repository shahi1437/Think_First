"use client";

import {
  Activity,
  AlertCircle,
  CheckCircle2,
  ShieldCheck,
  Users,
} from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  fetchAdminAuditLogs,
  fetchAdminUsers,
  grantAdminUserRole,
  revokeAdminUserRole,
} from "@/lib/api-client";
import type { AdminAuditLogItem, AdminUserSummary } from "@/types/admin";
import { formatUtcDateTime } from "@/lib/format-date";

interface AuditAccessClientProps {
  accessToken: string;
  initialUsers: AdminUserSummary[];
  initialLogs: AdminAuditLogItem[];
}

export function AuditAccessClient({
  accessToken,
  initialUsers,
  initialLogs,
}: AuditAccessClientProps) {
  const [users, setUsers] = useState<AdminUserSummary[]>(initialUsers);
  const [logs, setLogs] = useState<AdminAuditLogItem[]>(initialLogs);
  const [roleFilter, setRoleFilter] = useState<
    "all" | "student" | "teacher" | "admin"
  >("all");
  const [userSearch, setUserSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  async function refreshUsersAndLogs(
    nextRole: "all" | "student" | "teacher" | "admin" = roleFilter,
    nextSearch: string = userSearch,
  ) {
    const [uRes, lRes] = await Promise.all([
      fetchAdminUsers(accessToken, {
        limit: 50,
        role: nextRole === "all" ? undefined : nextRole,
        q: nextSearch.trim() || undefined,
      }),
      fetchAdminAuditLogs(accessToken, {
        action_prefix: actionFilter.trim() || undefined,
        limit: 50,
      }),
    ]);
    setUsers(uRes.items);
    setLogs(lRes.items);
  }

  async function handleFilterUsers(
    nextRole: "all" | "student" | "teacher" | "admin" = roleFilter,
    nextSearch: string = userSearch,
  ) {
    setBusy("filter-users");
    setErrorMsg(null);
    try {
      const uRes = await fetchAdminUsers(accessToken, {
        limit: 50,
        role: nextRole === "all" ? undefined : nextRole,
        q: nextSearch.trim() || undefined,
      });
      setUsers(uRes.items);
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to filter users.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleGrant(userId: string, role: "teacher" | "admin") {
    setBusy(`grant-${userId}-${role}`);
    setErrorMsg(null);
    setFeedback(null);
    try {
      await grantAdminUserRole(accessToken, userId, role);
      await refreshUsersAndLogs();
      setFeedback(`Granted '${role}' role and recorded immutable audit event.`);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Role grant failed.");
    } finally {
      setBusy(null);
    }
  }

  async function handleRevoke(userId: string, role: "teacher" | "admin") {
    if (
      role === "admin" &&
      !window.confirm(
        "Revoke admin role? Last-admin protection prevents removing the final platform administrator.",
      )
    ) {
      return;
    }
    setBusy(`revoke-${userId}-${role}`);
    setErrorMsg(null);
    setFeedback(null);
    try {
      await revokeAdminUserRole(accessToken, userId, role);
      await refreshUsersAndLogs();
      setFeedback(`Revoked '${role}' role and recorded immutable audit event.`);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Role revoke failed.");
    } finally {
      setBusy(null);
    }
  }

  async function handleFilterLogs() {
    setBusy("filter-logs");
    setErrorMsg(null);
    try {
      const lRes = await fetchAdminAuditLogs(accessToken, {
        action_prefix: actionFilter.trim() || undefined,
        limit: 50,
      });
      setLogs(lRes.items);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Log filter failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
          Security Governance &amp; Traceability
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">
          User Role Authorizations &amp; Immutable Audit Logs
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Every role elevation, validation, approval, rejection, publish, and
          archive action is permanently logged with actor &amp; request ID.
        </p>
      </section>

      {errorMsg ? (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-900"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
          <span>{errorMsg}</span>
        </div>
      ) : null}

      {feedback ? (
        <div
          role="status"
          className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-950"
        >
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-700" />
          <span>{feedback}</span>
        </div>
      ) : null}

      {/* Role Management Table */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-base font-bold text-slate-900">
              <Users className="h-4 w-4 text-indigo-600" />
              <span>Platform Users &amp; DB-Backed Roles ({users.length})</span>
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              Teacher provisioning: verify the instructor has registered an
              account, search their email below, and grant the{" "}
              <strong>teacher</strong> role.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            <select
              aria-label="Filter users by role"
              value={roleFilter}
              onChange={(e) => {
                const next = e.target.value as
                  | "all"
                  | "student"
                  | "teacher"
                  | "admin";
                setRoleFilter(next);
                void handleFilterUsers(next, userSearch);
              }}
              className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 font-medium text-slate-800"
            >
              <option value="all">All Roles</option>
              <option value="student">Students</option>
              <option value="teacher">Teachers</option>
              <option value="admin">Admins</option>
            </select>
            <input
              type="text"
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              placeholder="Search name or email..."
              className="rounded-lg border border-slate-300 px-3 py-1.5"
            />
            <button
              type="button"
              disabled={busy !== null}
              onClick={() => void handleFilterUsers(roleFilter, userSearch)}
              className="rounded-lg bg-[#0b1221] px-3 py-1.5 font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
            >
              Search
            </button>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-2 pr-4 font-semibold">User</th>
                <th className="py-2 pr-4 font-semibold">Roles</th>
                <th className="py-2 font-semibold">Privileged Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {users.map((u) => {
                const isTeacher = u.roles.includes("teacher");
                const isAdmin = u.roles.includes("admin");
                return (
                  <tr key={u.id}>
                    <td className="py-2.5 pr-4">
                      <p className="font-semibold text-slate-900">
                        {u.full_name || "Unnamed User"}
                      </p>
                      <p className="font-mono text-[11px] text-slate-500">
                        {u.email}
                      </p>
                    </td>
                    <td className="py-2.5 pr-4">
                      <div className="flex flex-wrap gap-1.5">
                        {u.roles.map((r) => (
                          <Badge
                            key={r}
                            variant={
                              r === "admin"
                                ? "indigo"
                                : r === "teacher"
                                  ? "teal"
                                  : "neutral"
                            }
                          >
                            {r}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="py-2.5">
                      <div className="flex flex-wrap gap-2">
                        {isTeacher ? (
                          <button
                            type="button"
                            disabled={busy !== null}
                            onClick={() => void handleRevoke(u.id, "teacher")}
                            className="rounded-lg border border-slate-300 px-2.5 py-1 font-semibold text-slate-700 hover:bg-slate-100"
                          >
                            Revoke Teacher
                          </button>
                        ) : (
                          <button
                            type="button"
                            disabled={busy !== null}
                            onClick={() => void handleGrant(u.id, "teacher")}
                            className="rounded-lg bg-teal-600 px-2.5 py-1 font-semibold text-white hover:bg-teal-700"
                          >
                            Grant Teacher
                          </button>
                        )}
                        {isAdmin ? (
                          <button
                            type="button"
                            disabled={busy !== null}
                            onClick={() => void handleRevoke(u.id, "admin")}
                            className="rounded-lg border border-rose-300 px-2.5 py-1 font-semibold text-rose-700 hover:bg-rose-50"
                          >
                            Revoke Admin
                          </button>
                        ) : (
                          <button
                            type="button"
                            disabled={busy !== null}
                            onClick={() => void handleGrant(u.id, "admin")}
                            className="inline-flex items-center gap-1 rounded-lg border border-indigo-300 bg-indigo-50 px-2.5 py-1 font-semibold text-indigo-800 hover:bg-indigo-100"
                          >
                            <ShieldCheck className="h-3 w-3" />
                            <span>Grant Admin</span>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Audit Log Stream */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-base font-bold text-slate-900">
            <Activity className="h-4 w-4 text-teal-600" />
            <span>Immutable Audit Log ({logs.length})</span>
          </h2>
          <div className="flex items-center gap-2 text-xs">
            <input
              type="text"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              placeholder="Filter prefix (e.g. problem., role.)"
              className="rounded-lg border border-slate-300 px-3 py-1.5"
            />
            <button
              type="button"
              onClick={() => void handleFilterLogs()}
              className="rounded-lg bg-slate-900 px-3 py-1.5 font-semibold text-white"
            >
              Filter
            </button>
          </div>
        </div>

        <div className="mt-4 space-y-2">
          {logs.map((log) => (
            <div
              key={log.id}
              className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-mono font-bold text-indigo-900">
                  {log.action}
                </span>
                <span className="text-[11px] text-slate-500">
                  {formatUtcDateTime(log.created_at)}
                </span>
              </div>
              <p className="mt-1 text-slate-700">
                Actor:{" "}
                <strong>
                  {log.actor_email || log.actor_user_id || "system"}
                </strong>{" "}
                · Target: <span className="font-mono">{log.target_type}</span> (
                <span className="font-mono text-[11px]">{log.target_id}</span>)
              </p>
              {Object.keys(log.metadata).length > 0 ? (
                <p className="mt-1 truncate font-mono text-[11px] text-slate-500">
                  {JSON.stringify(log.metadata)}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
