"use client";

import {
  AlertCircle,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  KeyRound,
  Loader2,
  Megaphone,
  Plus,
  Send,
  UserCheck,
  UserMinus,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  createClassInvitation,
  fetchTeacherStudentPerformance,
  manageClassMembership,
  postTeacherClassAnnouncement,
  revokeClassInvitation,
  updateTeacherClass,
} from "@/lib/api-client";
import type {
  EnrollmentPolicy,
  TeacherCourseDetailView,
  TeacherStudentPerformanceView,
} from "@/types/classroom";

interface TeacherClassDetailClientProps {
  accessToken: string;
  initialDetail: TeacherCourseDetailView;
}

export function TeacherClassDetailClient({
  accessToken,
  initialDetail,
}: TeacherClassDetailClientProps) {
  const [detail, setDetail] = useState<TeacherCourseDetailView>(initialDetail);
  const [title, setTitle] = useState(initialDetail.course.title);
  const [term, setTerm] = useState(initialDetail.course.term);
  const [policy, setPolicy] = useState<EnrollmentPolicy>(
    initialDetail.course.enrollment_policy,
  );
  const [savingCourse, setSavingCourse] = useState(false);
  const [creatingInvite, setCreatingInvite] = useState(false);
  const [busyMemberId, setBusyMemberId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [annTitle, setAnnTitle] = useState("");
  const [annBody, setAnnBody] = useState("");
  const [sendingAnn, setSendingAnn] = useState(false);
  const [annSuccess, setAnnSuccess] = useState<string | null>(null);
  const [selectedStudentPerf, setSelectedStudentPerf] =
    useState<TeacherStudentPerformanceView | null>(null);
  const [loadingStudentId, setLoadingStudentId] = useState<string | null>(null);
  const [studentPerfError, setStudentPerfError] = useState<string | null>(null);
  const inspectSeqRef = useRef(0);

  async function handleInspectStudent(studentId: string) {
    const seq = ++inspectSeqRef.current;
    setStudentPerfError(null);
    setLoadingStudentId(studentId);
    try {
      const perf = await fetchTeacherStudentPerformance(
        accessToken,
        detail.course.id,
        studentId,
      );
      if (seq !== inspectSeqRef.current) return;
      setSelectedStudentPerf(perf);
    } catch (err) {
      if (seq !== inspectSeqRef.current) return;
      setStudentPerfError(
        err instanceof Error
          ? err.message
          : "Could not load student performance breakdown.",
      );
    } finally {
      if (seq === inspectSeqRef.current) {
        setLoadingStudentId(null);
      }
    }
  }

  async function handleSendAnnouncement(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setAnnSuccess(null);
    if (annTitle.trim().length < 2 || annBody.trim().length < 4) {
      setError("Please enter an announcement title and message.");
      return;
    }
    setSendingAnn(true);
    try {
      const res = await postTeacherClassAnnouncement(
        accessToken,
        detail.course.id,
        { title: annTitle.trim(), body: annBody.trim() },
      );
      setAnnTitle("");
      setAnnBody("");
      setAnnSuccess(
        `Announcement "${res.title}" delivered to ${res.recipients_notified} active student(s).`,
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not send announcement.",
      );
    } finally {
      setSendingAnn(false);
    }
  }

  async function handleSaveCourse(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSavingCourse(true);
    try {
      const updated = await updateTeacherClass(accessToken, detail.course.id, {
        title: title.trim(),
        term: term.trim(),
        enrollment_policy: policy,
      });
      setDetail((prev) => ({ ...prev, course: updated }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update class.");
    } finally {
      setSavingCourse(false);
    }
  }

  async function handleNewInvite() {
    setError(null);
    setCreatingInvite(true);
    try {
      const inv = await createClassInvitation(accessToken, detail.course.id, {
        expires_in_hours: 168,
      });
      setDetail((prev) => ({
        ...prev,
        invitations: [inv, ...prev.invitations],
      }));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not generate invite code.",
      );
    } finally {
      setCreatingInvite(false);
    }
  }

  async function handleRevokeInvite(invitationId: string) {
    setError(null);
    try {
      const revoked = await revokeClassInvitation(
        accessToken,
        detail.course.id,
        invitationId,
      );
      setDetail((prev) => ({
        ...prev,
        invitations: prev.invitations.map((i) =>
          i.id === revoked.id ? revoked : i,
        ),
      }));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not revoke invite code.",
      );
    }
  }

  async function handleMembership(
    membershipId: string,
    action: "approve" | "remove",
  ) {
    setError(null);
    setBusyMemberId(membershipId);
    try {
      const updated = await manageClassMembership(
        accessToken,
        detail.course.id,
        membershipId,
        action,
      );
      setDetail((prev) => ({
        ...prev,
        roster: prev.roster.map((m) =>
          m.membership_id === updated.membership_id
            ? { ...m, status: updated.status, approved_at: updated.approved_at }
            : m,
        ),
      }));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not update membership.",
      );
    } finally {
      setBusyMemberId(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <Link
          href="/teacher/classes"
          className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-700 hover:underline"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to My Classes</span>
        </Link>

        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded bg-indigo-100 px-2 py-0.5 font-mono text-xs font-bold text-indigo-900">
                {detail.course.code}
              </span>
              <Badge
                variant={detail.course.status === "active" ? "teal" : "neutral"}
              >
                {detail.course.status}
              </Badge>
            </div>
            <h1 className="mt-1.5 text-2xl font-bold text-slate-900">
              {detail.course.title}
            </h1>
          </div>

          <Link
            href="/teacher/assignments"
            className="rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-indigo-500"
          >
            + Create Assignment for Class
          </Link>
        </div>

        <form
          onSubmit={(e) => void handleSaveCourse(e)}
          className="mt-4 grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3.5 sm:grid-cols-4"
        >
          <div>
            <label
              htmlFor="edit-class-title"
              className="block text-[11px] font-semibold text-slate-600"
            >
              Class Title
            </label>
            <input
              id="edit-class-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
            />
          </div>
          <div>
            <label
              htmlFor="edit-class-term"
              className="block text-[11px] font-semibold text-slate-600"
            >
              Term
            </label>
            <input
              id="edit-class-term"
              type="text"
              value={term}
              onChange={(e) => setTerm(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
            />
          </div>
          <div>
            <label
              htmlFor="edit-class-policy"
              className="block text-[11px] font-semibold text-slate-600"
            >
              Enrollment Policy
            </label>
            <select
              id="edit-class-policy"
              value={policy}
              onChange={(e) => setPolicy(e.target.value as EnrollmentPolicy)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
            >
              <option value="open_with_code">Auto-Enroll with Code</option>
              <option value="approval_required">Approval Required</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={savingCourse}
              className="w-full rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-700"
            >
              {savingCourse ? "Saving..." : "Save Class Settings"}
            </button>
          </div>
        </form>

        {error ? (
          <div
            role="alert"
            className="mt-3 flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800"
          >
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}
      </section>

      {/* Class Announcement Composer -> In-App Student Notification Center */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <Megaphone className="h-4 w-4 text-teal-700" aria-hidden="true" />
              <span>Send Class Announcement</span>
            </h2>
            <p className="mt-0.5 text-xs text-slate-600">
              Delivers an immediate in-app notification to all active students
              in {detail.course.code}.
            </p>
          </div>
        </div>

        <form
          onSubmit={(e) => void handleSendAnnouncement(e)}
          data-testid="teacher-announcement-form"
          className="mt-3 space-y-3"
        >
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="sm:col-span-1">
              <label
                htmlFor="class-announcement-title"
                className="block text-xs font-medium text-slate-700"
              >
                Title
              </label>
              <input
                id="class-announcement-title"
                type="text"
                value={annTitle}
                onChange={(e) => setAnnTitle(e.target.value)}
                placeholder="e.g. Lab 3 deadline reminder"
                maxLength={140}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-teal-600 focus:outline-none"
              />
            </div>
            <div className="sm:col-span-2">
              <label
                htmlFor="class-announcement-body"
                className="block text-xs font-medium text-slate-700"
              >
                Message
              </label>
              <input
                id="class-announcement-body"
                type="text"
                value={annBody}
                onChange={(e) => setAnnBody(e.target.value)}
                placeholder="Share lab instructions, office hours, or deadline updates..."
                maxLength={800}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-teal-600 focus:outline-none"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2">
            {annSuccess ? (
              <p
                role="status"
                data-testid="teacher-announcement-success"
                className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700"
              >
                <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                <span>{annSuccess}</span>
              </p>
            ) : (
              <span className="text-[11px] text-slate-500">
                Visible in enrolled students&apos; Notification Center.
              </span>
            )}
            <button
              type="submit"
              disabled={sendingAnn}
              data-testid="teacher-announcement-submit"
              className="inline-flex items-center gap-1.5 rounded-lg bg-[#0b1221] px-3.5 py-2 text-xs font-semibold text-white transition-colors hover:bg-slate-800 disabled:opacity-60"
            >
              {sendingAnn ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Send className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              <span>{sendingAnn ? "Sending..." : "Post Announcement"}</span>
            </button>
          </div>
        </form>
      </section>

      {/* Invitation Codes & Student Roster */}
      <section className="grid gap-6 lg:grid-cols-12">
        <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-5">
          <div className="flex items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <KeyRound className="h-4 w-4 text-indigo-600" />
              <span>Class Invitation Codes</span>
            </h2>
            <button
              type="button"
              disabled={creatingInvite}
              onClick={() => void handleNewInvite()}
              className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500"
            >
              {creatingInvite ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Plus className="h-3.5 w-3.5" />
              )}
              <span>Generate Invite Code</span>
            </button>
          </div>

          <div className="space-y-2">
            {detail.invitations.map((inv) => (
              <div
                key={inv.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs"
              >
                <div>
                  <p
                    data-testid="invite-code-preview"
                    className="font-mono text-sm font-bold text-indigo-950"
                  >
                    {inv.code_preview}
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Uses: {inv.uses_count}
                    {inv.max_uses ? ` / ${inv.max_uses}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={inv.is_active ? "teal" : "neutral"}>
                    {inv.is_active ? "Active" : "Revoked"}
                  </Badge>
                  {inv.is_active ? (
                    <button
                      type="button"
                      onClick={() => void handleRevokeInvite(inv.id)}
                      className="rounded border border-rose-200 bg-white px-2 py-1 text-[11px] font-semibold text-rose-700 hover:bg-rose-50"
                    >
                      Revoke
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-7">
          <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <Users className="h-4 w-4 text-teal-600" />
            <span>Student Roster ({detail.roster.length})</span>
          </h2>

          {detail.roster.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500">
              No students have joined yet. Share an active invitation code above.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[480px] text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="py-2 pr-3 font-semibold">Student</th>
                    <th className="py-2 pr-3 font-semibold">Status</th>
                    <th className="py-2 pr-3 font-semibold">Judge0 Attempts</th>
                    <th className="py-2 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {detail.roster.map((m) => (
                    <tr key={m.membership_id}>
                      <td className="py-2.5 pr-3">
                        <p className="font-bold text-slate-900">{m.full_name}</p>
                        <p className="text-[11px] text-slate-500">{m.email}</p>
                      </td>
                      <td className="py-2.5 pr-3">
                        <Badge
                          variant={
                            m.status === "active"
                              ? "teal"
                              : m.status === "pending"
                                ? "amber"
                                : "neutral"
                          }
                        >
                          {m.status}
                        </Badge>
                      </td>
                      <td className="py-2.5 pr-3 text-slate-700">
                        {m.accepted_attempts_count} accepted /{" "}
                        {m.submissions_count} total · {m.hints_used_total} hints
                      </td>
                      <td className="py-2.5">
                        <div className="flex flex-wrap gap-1.5">
                          <button
                            type="button"
                            disabled={loadingStudentId === m.student_id}
                            aria-label={`Inspect performance for ${m.full_name}`}
                            onClick={() =>
                              void handleInspectStudent(m.student_id)
                            }
                            className="inline-flex items-center gap-1 rounded border border-indigo-200 bg-indigo-50 px-2 py-1 text-[11px] font-semibold text-indigo-800 hover:bg-indigo-100 disabled:opacity-60"
                          >
                            {loadingStudentId === m.student_id ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <BarChart3 className="h-3 w-3" />
                            )}
                            <span>Inspect Performance</span>
                          </button>
                          {m.status !== "active" ? (
                            <button
                              type="button"
                              disabled={busyMemberId === m.membership_id}
                              onClick={() =>
                                void handleMembership(m.membership_id, "approve")
                              }
                              className="inline-flex items-center gap-1 rounded bg-teal-600 px-2 py-1 text-[11px] font-semibold text-white hover:bg-teal-500"
                            >
                              <UserCheck className="h-3 w-3" />
                              <span>Approve</span>
                            </button>
                          ) : null}
                          {m.status !== "removed" ? (
                            <button
                              type="button"
                              disabled={busyMemberId === m.membership_id}
                              onClick={() =>
                                void handleMembership(m.membership_id, "remove")
                              }
                              className="inline-flex items-center gap-1 rounded border border-rose-200 bg-white px-2 py-1 text-[11px] font-semibold text-rose-700 hover:bg-rose-50"
                            >
                              <UserMinus className="h-3 w-3" />
                              <span>Remove</span>
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {studentPerfError ? (
            <div
              role="alert"
              className="mt-3 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800"
            >
              {studentPerfError}
            </div>
          ) : null}

          {selectedStudentPerf ? (
            <div
              data-testid="teacher-student-drilldown"
              aria-live="polite"
              className="mt-4 space-y-4 rounded-xl border border-indigo-200 bg-indigo-50/40 p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-slate-900">
                      {selectedStudentPerf.full_name} — Student Drill-Down
                    </h3>
                    <Badge
                      variant={
                        selectedStudentPerf.membership_status === "active"
                          ? "teal"
                          : "neutral"
                      }
                    >
                      {selectedStudentPerf.membership_status}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-slate-600">
                    {selectedStudentPerf.email} · Persisted class &amp; mastery
                    evidence
                  </p>
                </div>
                <button
                  type="button"
                  aria-label="Close student performance panel"
                  onClick={() => setSelectedStudentPerf(null)}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-100"
                >
                  <X className="h-3 w-3" />
                  <span>Close</span>
                </button>
              </div>

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                <div className="rounded-lg border border-slate-200 bg-white p-2.5 text-xs">
                  <p className="text-[11px] text-slate-500">
                    Assignment Attempts
                  </p>
                  <p className="mt-0.5 font-bold text-slate-900">
                    {selectedStudentPerf.accepted_assignment_attempts} accepted
                    / {selectedStudentPerf.total_assignment_attempts} total
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-white p-2.5 text-xs">
                  <p className="text-[11px] text-slate-500">AI Hints Used</p>
                  <p className="mt-0.5 font-bold text-slate-900">
                    {selectedStudentPerf.hints_used_total}
                  </p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-white p-2.5 text-xs">
                  <p className="text-[11px] text-slate-500">
                    Verified Independent Transfers
                  </p>
                  <p className="mt-0.5 font-bold text-emerald-700">
                    {selectedStudentPerf.verified_transfers_count}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-slate-200 bg-white p-3 text-xs">
                  <p className="font-semibold text-slate-900">
                    Verified Skills ({selectedStudentPerf.verified_skills.length})
                  </p>
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {selectedStudentPerf.verified_skills.length === 0 ? (
                      <span className="text-[11px] text-slate-500">
                        No verified independent skills recorded yet.
                      </span>
                    ) : (
                      selectedStudentPerf.verified_skills.map((skill) => (
                        <Badge key={skill} variant="teal">
                          {skill}
                        </Badge>
                      ))
                    )}
                  </div>
                </div>
                <div className="rounded-lg border border-slate-200 bg-white p-3 text-xs">
                  <p className="font-semibold text-slate-900">
                    Developing / Guided Skills (
                    {selectedStudentPerf.developing_skills.length})
                  </p>
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {selectedStudentPerf.developing_skills.length === 0 ? (
                      <span className="text-[11px] text-slate-500">
                        No active developing skill gaps recorded.
                      </span>
                    ) : (
                      selectedStudentPerf.developing_skills.map((skill) => (
                        <Badge key={skill} variant="amber">
                          {skill}
                        </Badge>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {selectedStudentPerf.common_misconceptions.length > 0 ? (
                <div className="rounded-lg border border-amber-200 bg-amber-50/70 p-3 text-xs">
                  <p className="font-semibold text-amber-950">
                    Recurring ML Diagnosed Misconceptions
                  </p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {selectedStudentPerf.common_misconceptions.map((m) => (
                      <span
                        key={m.error_code}
                        className="rounded-md border border-amber-300 bg-white px-2 py-0.5 text-[11px] font-medium text-amber-900"
                      >
                        {m.error_code} ({m.occurrences})
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="rounded-lg border border-slate-200 bg-white p-3 text-xs">
                <p className="mb-2 font-semibold text-slate-900">
                  Class Assignment Breakdown (
                  {selectedStudentPerf.assignments.length})
                </p>
                {selectedStudentPerf.assignments.length === 0 ? (
                  <p className="text-[11px] text-slate-500">
                    No published assignments in this class yet.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[440px] text-left text-[11px]">
                      <thead>
                        <tr className="border-b border-slate-200 text-slate-500">
                          <th className="py-1.5 pr-2 font-semibold">
                            Assignment
                          </th>
                          <th className="py-1.5 pr-2 font-semibold">Status</th>
                          <th className="py-1.5 pr-2 font-semibold">
                            Attempts / Verdict
                          </th>
                          <th className="py-1.5 font-semibold">Grade</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {selectedStudentPerf.assignments.map((a) => (
                          <tr key={a.assignment_id}>
                            <td className="py-1.5 pr-2 font-semibold text-slate-900">
                              <Link
                                href={`/teacher/assignments/${a.assignment_id}`}
                                className="text-indigo-700 hover:underline"
                              >
                                {a.title}
                              </Link>
                            </td>
                            <td className="py-1.5 pr-2">
                              <Badge variant="neutral">
                                {a.workflow_status}
                              </Badge>
                            </td>
                            <td className="py-1.5 pr-2 text-slate-700">
                              {a.attempts_used} attempts
                              {a.latest_verdict ? ` · ${a.latest_verdict}` : ""}
                            </td>
                            <td className="py-1.5 text-slate-700">
                              {a.marks_awarded != null
                                ? `${a.marks_awarded} / ${a.max_marks} (${a.grade_status ?? "draft"})`
                                : `Not graded (max ${a.max_marks})`}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </section>

      {/* Class Assignments List */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-bold text-slate-900">
          Class Assignments ({detail.assignments.length})
        </h2>
        <div className="mt-3 space-y-2">
          {detail.assignments.length === 0 ? (
            <p className="text-xs text-slate-500">
              No assignments created for this class yet.
            </p>
          ) : (
            detail.assignments.map((a) => (
              <div
                key={a.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900">{a.title}</span>
                    <Badge
                      variant={
                        a.status === "published"
                          ? "teal"
                          : a.status === "draft"
                            ? "amber"
                            : "neutral"
                      }
                    >
                      {a.status}
                    </Badge>
                  </div>
                  <p className="mt-0.5 text-slate-600">
                    Max Marks: {a.max_marks} · Submitted: {a.submitted_count}/
                    {a.enrolled_students_count} · Graded: {a.graded_count}
                  </p>
                </div>
                <Link
                  href={`/teacher/assignments/${a.id}`}
                  className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-3 py-1.5 font-semibold text-white hover:bg-slate-700"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>Review &amp; Grade</span>
                </Link>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
