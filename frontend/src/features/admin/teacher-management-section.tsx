"use client";

import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Copy,
  Loader2,
  MailPlus,
  RefreshCw,
  Search,
  ShieldCheck,
  UserCheck,
  UserPlus,
  Users,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  createAdminTeacherInvitation,
  fetchAdminTeacherManagement,
  grantAdminUserRole,
  lookupAdminTeacherByEmail,
  resendAdminTeacherInvitation,
  revokeAdminTeacherInvitation,
  revokeAdminUserRole,
} from "@/lib/api-client";
import type {
  AdminUserSummary,
  TeacherInvitationView,
  TeacherLookupResponse,
} from "@/types/admin";

interface TeacherManagementSectionProps {
  accessToken?: string;
  initialActiveTeachers?: AdminUserSummary[];
  initialInvitations?: TeacherInvitationView[];
  onTeachersChanged?: () => Promise<void> | void;
}

export function TeacherManagementSection({
  accessToken = "",
  initialActiveTeachers = [],
  initialInvitations = [],
  onTeachersChanged,
}: TeacherManagementSectionProps) {
  const [activeTeachers, setActiveTeachers] = useState<AdminUserSummary[]>(
    initialActiveTeachers,
  );
  const [invitations, setInvitations] =
    useState<TeacherInvitationView[]>(initialInvitations);
  const [emailInput, setEmailInput] = useState("");
  const [fullNameInput, setFullNameInput] = useState("");
  const [searchFilter, setSearchFilter] = useState("");
  const [lookupResult, setLookupResult] =
    useState<TeacherLookupResponse | null>(null);
  const [pendingGrantUser, setPendingGrantUser] =
    useState<AdminUserSummary | null>(null);
  const [latestAcceptPath, setLatestAcceptPath] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  async function refreshTeacherData(query: string = searchFilter) {
    if (!accessToken) return;
    const overview = await fetchAdminTeacherManagement(accessToken, {
      q: query.trim() || undefined,
      limit: 50,
    });
    setActiveTeachers(overview.active_teachers);
    setInvitations(overview.invitations);
    if (onTeachersChanged) {
      await onTeachersChanged();
    }
  }

  async function handleLookupEmail(e?: React.FormEvent) {
    if (e) e.preventDefault();
    const cleaned = emailInput.trim().toLowerCase();
    if (!cleaned) {
      setErrorMsg("Please enter a Teacher email address to check or invite.");
      return;
    }
    if (!accessToken) return;
    setBusyAction("lookup");
    setErrorMsg(null);
    setFeedback(null);
    setPendingGrantUser(null);
    setLatestAcceptPath(null);
    try {
      const result = await lookupAdminTeacherByEmail(accessToken, cleaned);
      setLookupResult(result);
      if (
        result.status === "existing_user_not_teacher" &&
        result.existing_user
      ) {
        setPendingGrantUser(result.existing_user);
      }
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Unable to inspect teacher email.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleConfirmGrantExistingTeacher(user: AdminUserSummary) {
    if (!accessToken) return;
    setBusyAction(`grant-${user.id}`);
    setErrorMsg(null);
    setFeedback(null);
    try {
      await grantAdminUserRole(accessToken, user.id, "teacher");
      await refreshTeacherData();
      const updatedLookup = await lookupAdminTeacherByEmail(
        accessToken,
        user.email,
      );
      setLookupResult(updatedLookup);
      setPendingGrantUser(null);
      setFeedback(
        `Granted Teacher access to ${user.full_name || user.email}. Existing roles were preserved and an immutable audit log was recorded.`,
      );
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to grant Teacher role.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleInviteNewTeacher(targetEmail?: string) {
    const emailToInvite = (targetEmail ?? emailInput).trim().toLowerCase();
    if (!emailToInvite) {
      setErrorMsg("Please enter an email address to invite a new Teacher.");
      return;
    }
    if (!accessToken) return;
    setBusyAction("invite");
    setErrorMsg(null);
    setFeedback(null);
    setLatestAcceptPath(null);
    try {
      const res = await createAdminTeacherInvitation(accessToken, {
        email: emailToInvite,
        full_name: fullNameInput.trim(),
        expires_in_days: 7,
      });
      await refreshTeacherData();
      setLatestAcceptPath(res.accept_path ?? null);
      const updatedLookup = await lookupAdminTeacherByEmail(
        accessToken,
        emailToInvite,
      ).catch(() => null);
      if (updatedLookup) setLookupResult(updatedLookup);
      setFeedback(
        res.invitation.delivery_status === "sent"
          ? `Teacher invitation sent to ${res.invitation.email}.`
          : `Pending Teacher invitation created for ${res.invitation.email} (Status: Pending / SMTP Delivery Blocked — share the verified acceptance link below).`,
      );
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Failed to create teacher invitation.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleResendInvitation(inv: TeacherInvitationView) {
    if (!accessToken) return;
    setBusyAction(`resend-${inv.id}`);
    setErrorMsg(null);
    setFeedback(null);
    setLatestAcceptPath(null);
    try {
      const res = await resendAdminTeacherInvitation(accessToken, inv.id);
      await refreshTeacherData();
      setLatestAcceptPath(res.accept_path ?? null);
      setFeedback(
        `Resent and rotated invitation token for ${inv.email} (valid until ${new Date(res.invitation.expires_at).toLocaleDateString()}).`,
      );
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Failed to resend teacher invitation.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleRevokeInvitation(inv: TeacherInvitationView) {
    if (!accessToken) return;
    setBusyAction(`revoke-inv-${inv.id}`);
    setErrorMsg(null);
    setFeedback(null);
    try {
      await revokeAdminTeacherInvitation(accessToken, inv.id);
      await refreshTeacherData();
      if (lookupResult?.email === inv.email) {
        const refreshed = await lookupAdminTeacherByEmail(
          accessToken,
          inv.email,
        ).catch(() => null);
        if (refreshed) setLookupResult(refreshed);
      }
      setFeedback(
        `Revoked pending teacher invitation for ${inv.email}. Its token can no longer be used.`,
      );
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Failed to revoke teacher invitation.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleRevokeActiveTeacher(teacher: AdminUserSummary) {
    if (!accessToken) return;
    setBusyAction(`revoke-role-${teacher.id}`);
    setErrorMsg(null);
    setFeedback(null);
    try {
      await revokeAdminUserRole(accessToken, teacher.id, "teacher");
      await refreshTeacherData();
      if (lookupResult?.email === teacher.email) {
        const refreshed = await lookupAdminTeacherByEmail(
          accessToken,
          teacher.email,
        ).catch(() => null);
        if (refreshed) setLookupResult(refreshed);
      }
      setFeedback(
        `Revoked Teacher access from ${teacher.full_name || teacher.email} and recorded an immutable audit log.`,
      );
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Failed to revoke Teacher role.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleSearchTeachers(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!accessToken) return;
    setBusyAction("search");
    setErrorMsg(null);
    try {
      await refreshTeacherData(searchFilter);
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to search teachers.",
      );
    } finally {
      setBusyAction(null);
    }
  }

  async function handleCopyAcceptLink(acceptPath: string) {
    const fullUrl =
      typeof window !== "undefined"
        ? `${window.location.origin}${acceptPath}`
        : acceptPath;
    try {
      await navigator.clipboard.writeText(fullUrl);
      setCopiedLink(true);
      window.setTimeout(() => setCopiedLink(false), 2500);
    } catch {
      setCopiedLink(false);
    }
  }

  const pendingInvitations = invitations.filter(
    (inv) => inv.status === "pending",
  );

  return (
    <section
      aria-label="Teacher Management"
      className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
            Instructor Access &amp; Invitations
          </p>
          <h2 className="mt-1 flex items-center gap-2 text-lg font-bold text-slate-900">
            <Users className="h-5 w-5 text-indigo-600" aria-hidden="true" />
            <span>TEACHER MANAGEMENT</span>
          </h2>
          <p className="mt-1 text-xs leading-relaxed text-slate-600">
            Add existing accounts as Teachers, invite new instructors via
            verified invitations, view Teacher status, or revoke Teacher access
            under strict server-side Admin RBAC.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <Badge variant="teal">
            Active Teachers: {activeTeachers.length}
          </Badge>
          <Badge variant="amber">
            Pending Invitations: {pendingInvitations.length}
          </Badge>
        </div>
      </div>

      {errorMsg ? (
        <div
          role="alert"
          className="mt-4 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-900"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
          <span>{errorMsg}</span>
        </div>
      ) : null}

      {feedback ? (
        <div
          role="status"
          className="mt-4 space-y-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3.5 text-xs text-emerald-950"
        >
          <div className="flex items-center gap-2 font-semibold">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-700" />
            <span>{feedback}</span>
          </div>
          {latestAcceptPath ? (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-emerald-200 bg-white px-3 py-2">
              <div className="min-w-0 flex-1">
                <p className="text-[11px] font-semibold text-slate-700">
                  Verified One-Time Teacher Invitation Link:
                </p>
                <p
                  data-testid="teacher-invite-accept-link"
                  className="truncate font-mono text-[11px] text-indigo-800"
                >
                  {latestAcceptPath}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => void handleCopyAcceptLink(latestAcceptPath)}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-800 hover:bg-slate-100"
                >
                  <Copy className="h-3 w-3" />
                  <span>{copiedLink ? "Copied!" : "Copy Link"}</span>
                </button>
                <Link
                  href={latestAcceptPath}
                  className="rounded-lg bg-indigo-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-indigo-500"
                >
                  Inspect Link
                </Link>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Add Teacher / Lookup Teacher by Email / Invite New Teacher */}
      <div className="mt-5 grid gap-5 lg:grid-cols-12">
        <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 lg:col-span-6">
          <h3 className="flex items-center gap-1.5 text-sm font-bold text-slate-900">
            <UserPlus className="h-4 w-4 text-teal-600" />
            <span>Add or Invite Teacher by Email</span>
          </h3>
          <p className="mt-1 text-xs text-slate-600">
            Enter an email to check if the account exists (Case A: confirm &amp;
            grant Teacher role) or send a verified Teacher Invitation (Case B:
            new instructor).
          </p>

          <form
            onSubmit={(e) => void handleLookupEmail(e)}
            className="mt-3 space-y-3"
          >
            <div className="grid gap-2.5 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="teacher-mgmt-email"
                  className="block text-xs font-semibold text-slate-700"
                >
                  Teacher email address
                </label>
                <input
                  id="teacher-mgmt-email"
                  type="email"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  placeholder="instructor@university.edu"
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-indigo-600 focus:outline-none"
                />
              </div>
              <div>
                <label
                  htmlFor="teacher-mgmt-name"
                  className="block text-xs font-semibold text-slate-700"
                >
                  Instructor name (optional, for invite)
                </label>
                <input
                  id="teacher-mgmt-name"
                  type="text"
                  value={fullNameInput}
                  onChange={(e) => setFullNameInput(e.target.value)}
                  placeholder="Dr. Farhana Ahmed"
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-indigo-600 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="submit"
                disabled={busyAction !== null}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[#0b1221] px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
              >
                {busyAction === "lookup" ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Search className="h-3.5 w-3.5" />
                )}
                <span>Check Email Status</span>
              </button>

              <button
                type="button"
                disabled={busyAction !== null}
                onClick={() => void handleInviteNewTeacher()}
                className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-60"
              >
                {busyAction === "invite" ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <MailPlus className="h-3.5 w-3.5" />
                )}
                <span>Invite New Teacher</span>
              </button>
            </div>
          </form>

          {/* Lookup / Status Result Card */}
          {lookupResult ? (
            <div
              data-testid="teacher-lookup-result"
              className="mt-4 space-y-2.5 rounded-xl border border-slate-200 bg-white p-3.5 text-xs"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-mono font-semibold text-slate-900">
                  {lookupResult.email}
                </span>
                <Badge
                  variant={
                    lookupResult.status === "active_teacher"
                      ? "emerald"
                      : lookupResult.status === "existing_user_not_teacher"
                        ? "indigo"
                        : lookupResult.status === "pending_invitation"
                          ? "amber"
                          : "neutral"
                  }
                >
                  {lookupResult.status.replaceAll("_", " ")}
                </Badge>
              </div>
              <p className="text-slate-700">{lookupResult.message}</p>

              {lookupResult.existing_user ? (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5">
                  <p className="font-semibold text-slate-900">
                    Account Identity:{" "}
                    {lookupResult.existing_user.full_name || "Unnamed User"} (
                    {lookupResult.existing_user.email})
                  </p>
                  <p className="mt-0.5 text-[11px] text-slate-600">
                    Current Roles:{" "}
                    <span className="font-mono font-semibold">
                      {lookupResult.existing_user.roles.join(", ")}
                    </span>{" "}
                    · Onboarded:{" "}
                    {lookupResult.existing_user.onboarding_completed
                      ? "Yes"
                      : "No"}
                  </p>
                </div>
              ) : null}

              {pendingGrantUser ? (
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-teal-200 bg-teal-50 p-2.5">
                  <span className="font-medium text-teal-950">
                    Confirm granting <strong>teacher</strong> role to{" "}
                    {pendingGrantUser.email}?
                  </span>
                  <button
                    type="button"
                    disabled={busyAction !== null}
                    onClick={() =>
                      void handleConfirmGrantExistingTeacher(pendingGrantUser)
                    }
                    className="inline-flex items-center gap-1 rounded-lg bg-teal-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-800 disabled:opacity-60"
                  >
                    <UserCheck className="h-3.5 w-3.5" />
                    <span>Confirm &amp; Grant Teacher Role</span>
                  </button>
                </div>
              ) : null}

              {lookupResult.can_invite ? (
                <div className="pt-1">
                  <button
                    type="button"
                    disabled={busyAction !== null}
                    onClick={() =>
                      void handleInviteNewTeacher(lookupResult.email)
                    }
                    className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
                  >
                    <MailPlus className="h-3.5 w-3.5" />
                    <span>Create Pending Invitation for {lookupResult.email}</span>
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        {/* Search & Filter Bar + Quick Governance Summary */}
        <div className="flex flex-col justify-between rounded-xl border border-slate-200 bg-slate-50/80 p-4 lg:col-span-6">
          <div>
            <h3 className="flex items-center gap-1.5 text-sm font-bold text-slate-900">
              <Search className="h-4 w-4 text-indigo-600" />
              <span>Search Active Teachers &amp; Invitations</span>
            </h3>
            <p className="mt-1 text-xs text-slate-600">
              Filter active teachers and pending/historical invitations by email
              or instructor name.
            </p>

            <form
              onSubmit={(e) => void handleSearchTeachers(e)}
              className="mt-3 flex flex-wrap items-center gap-2"
            >
              <input
                type="text"
                aria-label="Search teachers by email"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Filter by teacher email or name..."
                className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-indigo-600 focus:outline-none"
              />
              <button
                type="submit"
                disabled={busyAction !== null}
                className="rounded-lg bg-[#0b1221] px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
              >
                Filter
              </button>
              {searchFilter ? (
                <button
                  type="button"
                  disabled={busyAction !== null}
                  onClick={() => {
                    setSearchFilter("");
                    void refreshTeacherData("");
                  }}
                  className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Reset
                </button>
              ) : null}
            </form>
          </div>

          <div className="mt-4 rounded-xl border border-slate-200 bg-white p-3.5 text-xs text-slate-600">
            <div className="flex items-center gap-1.5 font-semibold text-slate-900">
              <ShieldCheck className="h-4 w-4 text-teal-600" />
              <span>Strict Role Separation &amp; Audit Guarantee</span>
            </div>
            <p className="mt-1 leading-relaxed">
              Granting or accepting a Teacher invitation assigns{" "}
              <strong>only</strong> the <code className="font-mono">teacher</code>{" "}
              role in <code className="font-mono">public.user_roles</code>{" "}
              (never <code className="font-mono">admin</code>), preserves
              existing student progress, and writes an immutable record to{" "}
              <code className="font-mono">public.audit_logs</code>.
            </p>
          </div>
        </div>
      </div>

      {/* Active Teachers List & Pending Invitations List */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {/* View Active Teachers */}
        <div className="rounded-xl border border-slate-200 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900">
              Active Teachers ({activeTeachers.length})
            </h3>
            <Badge variant="teal">DB-Backed Teacher Role</Badge>
          </div>

          {activeTeachers.length === 0 ? (
            <p className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
              No active Teacher accounts found matching your filter. Use the
              form above to grant Teacher access to an existing user or invite a
              new instructor.
            </p>
          ) : (
            <div className="mt-3 divide-y divide-slate-100">
              {activeTeachers.map((teacher) => (
                <div
                  key={teacher.id}
                  data-testid={`active-teacher-row-${teacher.email}`}
                  className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-xs"
                >
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900">
                      {teacher.full_name || "Instructor"}
                    </p>
                    <p className="truncate font-mono text-[11px] text-slate-500">
                      {teacher.email}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-1">
                      <Badge variant="emerald">Active Teacher</Badge>
                      {teacher.roles.map((role) => (
                        <Badge
                          key={role}
                          variant={
                            role === "admin"
                              ? "indigo"
                              : role === "teacher"
                                ? "teal"
                                : "neutral"
                          }
                        >
                          {role}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <button
                    type="button"
                    disabled={busyAction !== null}
                    onClick={() => void handleRevokeActiveTeacher(teacher)}
                    className="inline-flex items-center gap-1 rounded-lg border border-rose-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-rose-700 transition hover:bg-rose-50 disabled:opacity-60"
                  >
                    <XCircle className="h-3.5 w-3.5" />
                    <span>Revoke Teacher Access</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* View Pending & Historical Invitations */}
        <div className="rounded-xl border border-slate-200 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900">
              Teacher Invitations ({invitations.length})
            </h3>
            <Badge variant="amber">
              {pendingInvitations.length} Pending
            </Badge>
          </div>

          {invitations.length === 0 ? (
            <p className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
              No teacher invitations recorded yet. Enter an unregistered
              instructor email above and click{" "}
              <strong>Invite New Teacher</strong>.
            </p>
          ) : (
            <div className="mt-3 divide-y divide-slate-100">
              {invitations.map((inv) => (
                <div
                  key={inv.id}
                  data-testid={`teacher-invitation-row-${inv.email}`}
                  className="space-y-1.5 py-2.5 text-xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <span className="font-semibold text-slate-900">
                        {inv.full_name || inv.email}
                      </span>
                      {inv.full_name ? (
                        <span className="ml-1.5 font-mono text-[11px] text-slate-500">
                          ({inv.email})
                        </span>
                      ) : null}
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge
                        variant={
                          inv.status === "accepted"
                            ? "emerald"
                            : inv.status === "pending"
                              ? "amber"
                              : "rose"
                        }
                      >
                        {inv.status}
                      </Badge>
                      <Badge
                        variant={
                          inv.delivery_status === "sent" ? "teal" : "neutral"
                        }
                      >
                        {inv.delivery_status === "sent"
                          ? "Email Sent"
                          : "Pending / Delivery Blocked"}
                      </Badge>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-500">
                    <Clock className="mr-1 inline h-3 w-3" />
                    Expires: {new Date(inv.expires_at).toLocaleDateString()} ·
                    Token: <code className="font-mono">{inv.token_preview}</code>
                    {inv.resend_count > 0
                      ? ` · Resent ${inv.resend_count}x`
                      : ""}
                  </p>

                  {inv.status === "pending" || inv.status === "expired" ? (
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <button
                        type="button"
                        disabled={busyAction !== null}
                        onClick={() => void handleResendInvitation(inv)}
                        className="inline-flex items-center gap-1 rounded-lg border border-indigo-300 bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-800 hover:bg-indigo-100 disabled:opacity-60"
                      >
                        <RefreshCw className="h-3 w-3" />
                        <span>Resend Invitation</span>
                      </button>
                      {inv.status === "pending" ? (
                        <button
                          type="button"
                          disabled={busyAction !== null}
                          onClick={() => void handleRevokeInvitation(inv)}
                          className="inline-flex items-center gap-1 rounded-lg border border-rose-300 bg-white px-2.5 py-1 text-[11px] font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-60"
                        >
                          <XCircle className="h-3 w-3" />
                          <span>Revoke Invitation</span>
                        </button>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
