"use client";

import {
  AlertCircle,
  Archive,
  ArrowLeft,
  CheckCircle2,
  History,
  Loader2,
  Send,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  archiveTeacherAssignment,
  gradeStudentSubmission,
  publishTeacherAssignment,
} from "@/lib/api-client";
import type {
  TeacherAssignmentDetailView,
  TeacherSubmissionReviewItem,
} from "@/types/classroom";

interface TeacherAssignmentReviewClientProps {
  accessToken: string;
  initialDetail: TeacherAssignmentDetailView;
}

export function TeacherAssignmentReviewClient({
  accessToken,
  initialDetail,
}: TeacherAssignmentReviewClientProps) {
  const [detail, setDetail] =
    useState<TeacherAssignmentDetailView>(initialDetail);
  const [selectedSubId, setSelectedSubId] = useState<string | null>(
    initialDetail.submissions[0]?.assignment_submission_id ?? null,
  );
  const [marks, setMarks] = useState<string>(() => {
    const first = initialDetail.submissions[0];
    return first?.grade
      ? String(first.grade.marks_awarded)
      : String(initialDetail.assignment.max_marks);
  });
  const [feedback, setFeedback] = useState("");
  const [gradingAction, setGradingAction] = useState<string | null>(null);
  const [statusBusy, setStatusBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeSub: TeacherSubmissionReviewItem | null =
    detail.submissions.find(
      (s) => s.assignment_submission_id === selectedSubId,
    ) ??
    detail.submissions[0] ??
    null;

  function selectSubmission(sub: TeacherSubmissionReviewItem) {
    setSelectedSubId(sub.assignment_submission_id);
    setMarks(
      sub.grade
        ? String(sub.grade.marks_awarded)
        : String(detail.assignment.max_marks),
    );
    setFeedback("");
    setError(null);
  }

  async function handlePublishOrArchive(target: "publish" | "archive") {
    setError(null);
    setStatusBusy(true);
    try {
      const updated =
        target === "publish"
          ? await publishTeacherAssignment(accessToken, detail.assignment.id)
          : await archiveTeacherAssignment(accessToken, detail.assignment.id);
      setDetail((prev) => ({ ...prev, assignment: updated }));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not update assignment status.",
      );
    } finally {
      setStatusBusy(false);
    }
  }

  async function handleGrade(
    action: "save_draft" | "publish" | "request_revision",
  ) {
    if (!activeSub) return;
    setError(null);
    setGradingAction(action);
    try {
      const numericMarks = Number(marks);
      const updatedItem = await gradeStudentSubmission(
        accessToken,
        activeSub.assignment_submission_id,
        {
          marks_awarded: Number.isFinite(numericMarks) ? numericMarks : 0,
          action,
          feedback_md: feedback,
        },
      );
      setDetail((prev) => ({
        ...prev,
        submissions: prev.submissions.map((s) =>
          s.assignment_submission_id === updatedItem.assignment_submission_id
            ? updatedItem
            : s,
        ),
      }));
      setFeedback("");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not save grade/feedback.",
      );
    } finally {
      setGradingAction(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <Link
          href="/teacher/assignments"
          className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-700 hover:underline"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to Assignments</span>
        </Link>

        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded bg-indigo-100 px-2 py-0.5 font-mono text-xs font-bold text-indigo-900">
                {detail.assignment.course_code}
              </span>
              <Badge
                variant={
                  detail.assignment.status === "published"
                    ? "teal"
                    : detail.assignment.status === "draft"
                      ? "amber"
                      : "neutral"
                }
              >
                {detail.assignment.status}
              </Badge>
              <Badge variant="indigo">
                Max Marks: {detail.assignment.max_marks} · Max Attempts:{" "}
                {detail.assignment.max_attempts}
              </Badge>
            </div>
            <h1 className="mt-1.5 text-2xl font-bold text-slate-900">
              {detail.assignment.title}
            </h1>
            <p className="mt-1 text-xs text-slate-600">
              {detail.instructions_md || "No instructions provided."}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {detail.assignment.status === "draft" ? (
              <button
                type="button"
                disabled={statusBusy}
                onClick={() => void handlePublishOrArchive("publish")}
                className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-teal-500"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Publish Assignment</span>
              </button>
            ) : null}
            {detail.assignment.status !== "archived" ? (
              <button
                type="button"
                disabled={statusBusy}
                onClick={() => void handlePublishOrArchive("archive")}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                <Archive className="h-3.5 w-3.5" />
                <span>Archive</span>
              </button>
            ) : null}
          </div>
        </div>

        {/* Linked Approved Problems */}
        <div className="mt-4 flex flex-wrap gap-2">
          {detail.problems.map((p) => (
            <div
              key={p.link_id}
              className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs"
            >
              <span className="font-bold text-slate-900">
                #{p.ordinal} {p.title}
              </span>{" "}
              <span className="text-slate-500">
                (v{p.version_number} · {p.mode} · {p.points} pts)
              </span>
            </div>
          ))}
        </div>

        {error ? (
          <div
            role="alert"
            className="mt-4 flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800"
          >
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}
      </section>

      {/* Submissions Roster & Grading Workspace */}
      {detail.submissions.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-xs text-slate-500">
          No student submissions recorded for this assignment yet.
        </section>
      ) : (
        <section className="grid gap-6 lg:grid-cols-12">
          {/* Left: Student Submissions List */}
          <div className="space-y-2.5 lg:col-span-4">
            <h2 className="text-sm font-bold text-slate-900">
              Student Submissions ({detail.submissions.length})
            </h2>
            {detail.submissions.map((sub) => {
              const isSelected =
                activeSub?.assignment_submission_id ===
                sub.assignment_submission_id;
              return (
                <button
                  key={sub.assignment_submission_id}
                  type="button"
                  onClick={() => selectSubmission(sub)}
                  className={`w-full rounded-2xl border p-4 text-left transition ${
                    isSelected
                      ? "border-indigo-600 bg-indigo-50/40 ring-1 ring-indigo-600"
                      : "border-slate-200 bg-white hover:border-indigo-300"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-sm font-bold text-slate-900">
                      {sub.student_name}
                    </span>
                    <Badge
                      variant={
                        sub.status === "graded"
                          ? "teal"
                          : sub.status === "revision_requested"
                            ? "amber"
                            : "indigo"
                      }
                    >
                      {sub.status}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-slate-500">
                    {sub.student_email}
                  </p>
                  <div className="mt-2 flex flex-wrap items-center justify-between text-xs text-slate-600">
                    <span>Attempts: {sub.attempts_used}</span>
                    {sub.grade ? (
                      <span className="font-bold text-teal-800">
                        {sub.grade.marks_awarded} / {sub.grade.max_marks} (
                        {sub.grade.status})
                      </span>
                    ) : (
                      <span>Not graded</span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Right: Code Inspector, Judge0 Verdicts, Grading Form & Audit Trail */}
          {activeSub ? (
            <div className="space-y-5 lg:col-span-8">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="text-base font-bold text-slate-900">
                      Reviewing: {activeSub.student_name}
                    </h2>
                    <p className="text-xs text-slate-500">
                      Workflow Status:{" "}
                      <span className="font-semibold text-slate-800">
                        {activeSub.status}
                      </span>{" "}
                      · Attempts Used: {activeSub.attempts_used}
                      {activeSub.is_late ? " · LATE SUBMISSION" : ""}
                    </p>
                  </div>
                  {activeSub.latest_attempt ? (
                    <Badge
                      variant={
                        activeSub.latest_attempt.verdict === "accepted"
                          ? "teal"
                          : "amber"
                      }
                    >
                      Judge0: {activeSub.latest_attempt.verdict} (
                      {activeSub.latest_attempt.passed_tests}/
                      {activeSub.latest_attempt.total_tests} tests)
                    </Badge>
                  ) : null}
                </div>

                {activeSub.latest_attempt ? (
                  <div className="mt-4 space-y-2">
                    <p className="text-xs font-semibold text-slate-700">
                      Latest Submitted Source Code (Attempt #
                      {activeSub.latest_attempt.attempt_number} ·{" "}
                      {new Date(
                        activeSub.latest_attempt.submitted_at,
                      ).toLocaleString()}
                      )
                    </p>
                    <pre className="max-h-72 overflow-auto rounded-xl bg-slate-950 p-3.5 font-mono text-xs text-slate-100">
                      <code>{activeSub.latest_attempt.source_code}</code>
                    </pre>
                    {activeSub.latest_attempt.student_notes ? (
                      <p className="rounded-lg bg-slate-50 p-2.5 text-xs text-slate-700">
                        <strong>Student Notes:</strong>{" "}
                        {activeSub.latest_attempt.student_notes}
                      </p>
                    ) : null}
                  </div>
                ) : null}

                {/* Teacher Grading & Feedback Controls */}
                <div className="mt-5 space-y-3 border-t border-slate-200 pt-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <label
                        htmlFor="grade-marks"
                        className="block text-xs font-semibold text-slate-700"
                      >
                        Marks Awarded (Max: {detail.assignment.max_marks})
                      </label>
                      <input
                        id="grade-marks"
                        type="number"
                        step="0.5"
                        min={0}
                        max={detail.assignment.max_marks}
                        value={marks}
                        onChange={(e) => setMarks(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900"
                      />
                    </div>
                  </div>

                  <div>
                    <label
                      htmlFor="grade-feedback"
                      className="block text-xs font-semibold text-slate-700"
                    >
                      Written Teacher Feedback (required when requesting
                      revision)
                    </label>
                    <textarea
                      id="grade-feedback"
                      rows={3}
                      value={feedback}
                      onChange={(e) => setFeedback(e.target.value)}
                      placeholder="Write constructive feedback on logic, edge cases, and code quality..."
                      className="mt-1 w-full rounded-xl border border-slate-300 bg-white p-2.5 text-xs text-slate-900"
                    />
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={gradingAction !== null}
                      onClick={() => void handleGrade("save_draft")}
                      className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                    >
                      {gradingAction === "save_draft"
                        ? "Saving Draft..."
                        : "Save Draft Grade"}
                    </button>
                    <button
                      type="button"
                      disabled={gradingAction !== null}
                      onClick={() => void handleGrade("request_revision")}
                      className="rounded-lg bg-amber-600 px-3 py-2 text-xs font-semibold text-white hover:bg-amber-500"
                    >
                      {gradingAction === "request_revision"
                        ? "Requesting..."
                        : "Request Revision"}
                    </button>
                    <button
                      type="button"
                      disabled={gradingAction !== null}
                      onClick={() => void handleGrade("publish")}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-teal-500"
                    >
                      {gradingAction === "publish" ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Send className="h-3.5 w-3.5" />
                      )}
                      <span>Publish Grade &amp; Feedback</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Feedback & Immutable Grading Audit Trail */}
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Feedback History ({activeSub.feedback.length})
                  </h3>
                  <div className="mt-2.5 space-y-2 text-xs">
                    {activeSub.feedback.length === 0 ? (
                      <p className="text-slate-500">No feedback posted yet.</p>
                    ) : (
                      activeSub.feedback.map((f) => (
                        <div
                          key={f.id}
                          className="rounded-lg border border-slate-200 bg-slate-50 p-2.5"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <Badge variant="indigo">{f.feedback_type}</Badge>
                            <span className="text-[10px] text-slate-500">
                              {new Date(f.created_at).toLocaleString()}
                            </span>
                          </div>
                          <p className="mt-1 text-slate-800">{f.body_md}</p>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <h3 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500">
                    <History className="h-3.5 w-3.5" />
                    <span>
                      Grading Audit Trail ({activeSub.audit_events.length})
                    </span>
                  </h3>
                  <div className="mt-2.5 space-y-2 text-xs">
                    {activeSub.audit_events.length === 0 ? (
                      <p className="text-slate-500">No audit events yet.</p>
                    ) : (
                      activeSub.audit_events.map((ev) => (
                        <div
                          key={ev.id}
                          className="rounded-lg border border-slate-200 bg-slate-50 p-2.5"
                        >
                          <p className="font-semibold text-slate-900">
                            {ev.action} ({ev.previous_marks ?? "none"} →{" "}
                            {ev.new_marks})
                          </p>
                          <p className="text-[11px] text-slate-600">
                            {ev.notes}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </section>
      )}
    </div>
  );
}
