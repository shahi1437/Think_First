"use client";

import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  Loader2,
  Play,
  Send,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { CodeEditor } from "@/features/workspace/code-editor";
import {
  createSubmission,
  fetchSubmissionDetail,
  saveWorkspaceRevision,
  submitStudentAssignment,
} from "@/lib/api-client";
import { formatUtcDateTime } from "@/lib/format-date";
import type {
  AssignmentAttemptView,
  StudentAssignmentDetailView,
} from "@/types/classroom";
import type { StudentProblemDetail, SubmissionResponse } from "@/types/problems";

interface StudentAssignmentDetailClientProps {
  accessToken: string;
  initialDetail: StudentAssignmentDetailView;
  problemsById: Record<string, StudentProblemDetail>;
  usePlainEditor?: boolean;
}

export function StudentAssignmentDetailClient({
  accessToken,
  initialDetail,
  problemsById,
  usePlainEditor = false,
}: StudentAssignmentDetailClientProps) {
  const [detail, setDetail] =
    useState<StudentAssignmentDetailView>(initialDetail);
  const [activeProblemId, setActiveProblemId] = useState<string>(
    initialDetail.problems[0]?.problem_id ?? "",
  );
  const [codeByProblem, setCodeByProblem] = useState<Record<string, string>>(
    () => {
      const map: Record<string, string> = {};
      for (const link of initialDetail.problems) {
        const latestAttempt = initialDetail.attempts.find(
          (a) => a.problem_id === link.problem_id,
        );
        const prob = problemsById[link.problem_id];
        const variant = prob?.variants[0];
        const starter =
          prob?.mode === "debugging" && variant?.buggy_starter_code
            ? variant.buggy_starter_code
            : (variant?.starter_code ?? "");
        map[link.problem_id] = latestAttempt?.source_code ?? starter;
      }
      return map;
    },
  );
  const [studentNotes, setStudentNotes] = useState("");
  const [runningJudge0, setRunningJudge0] = useState(false);
  const [submittingAttempt, setSubmittingAttempt] = useState(false);
  const [savingRevision, setSavingRevision] = useState(false);
  const [lastRunResult, setLastRunResult] = useState<SubmissionResponse | null>(
    null,
  );
  const [lastAttempt, setLastAttempt] = useState<AssignmentAttemptView | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  const activeProblem: StudentProblemDetail | undefined =
    problemsById[activeProblemId];
  const currentCode = codeByProblem[activeProblemId] ?? "";

  async function handleRunPublicTests() {
    if (!activeProblem) return;
    setError(null);
    setRunningJudge0(true);
    try {
      let res = await createSubmission(accessToken, {
        problem_id: activeProblem.problem_id,
        language_slug: "python",
        submission_kind: "run",
        source_code: currentCode,
      });
      setLastRunResult(res);
      const deadline = Date.now() + 65_000;
      while (
        (res.status === "queued" || res.status === "running") &&
        Date.now() < deadline
      ) {
        await new Promise((resolve) => window.setTimeout(resolve, 1200));
        res = await fetchSubmissionDetail(accessToken, res.id);
        setLastRunResult(res);
      }
      if (res.status === "queued" || res.status === "running") {
        setError(
          "Code execution timed out while waiting for the local Judge0 runner. Please check the runner status and try again.",
        );
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not run public tests.",
      );
    } finally {
      setRunningJudge0(false);
    }
  }

  async function handleSaveRevision() {
    if (!activeProblem) return;
    setError(null);
    setSavingRevision(true);
    try {
      await saveWorkspaceRevision(accessToken, {
        problem_version_id: activeProblem.version_id,
        language_slug: "python",
        source_code: currentCode,
        explanation_text: studentNotes || undefined,
        revision_type: "manual",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save revision.");
    } finally {
      setSavingRevision(false);
    }
  }

  async function handleSubmitAssignment() {
    if (!activeProblem) return;
    setError(null);
    setSubmittingAttempt(true);
    try {
      const resp = await submitStudentAssignment(
        accessToken,
        detail.assignment.assignment_id,
        {
          problem_id: activeProblem.problem_id,
          language_slug: "python",
          source_code: currentCode,
          student_notes: studentNotes.trim(),
          hints_used: 0,
        },
      );
      setLastAttempt(resp.attempt);
      setDetail((prev) => ({
        ...prev,
        assignment: {
          ...prev.assignment,
          workflow_status: resp.workflow_status,
          attempts_used: resp.attempts_used,
        },
        attempts: [resp.attempt, ...prev.attempts],
        can_submit: resp.attempts_remaining > 0,
      }));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not submit assignment attempt.",
      );
    } finally {
      setSubmittingAttempt(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header & Policy Summary */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <Link
          href="/student/assignments"
          className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-700 hover:underline"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back to My Assignments</span>
        </Link>

        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded bg-indigo-100 px-2 py-0.5 font-mono text-xs font-bold text-indigo-900">
                {detail.assignment.course_code}
              </span>
              <Badge
                variant={
                  detail.assignment.workflow_status === "graded"
                    ? "teal"
                    : detail.assignment.workflow_status === "revision_requested"
                      ? "amber"
                      : "indigo"
                }
              >
                {detail.assignment.workflow_status.replaceAll("_", " ")}
              </Badge>
              <Badge variant="neutral">
                Attempts: {detail.assignment.attempts_used} /{" "}
                {detail.assignment.max_attempts}
              </Badge>
              <Badge variant="indigo">
                Max Marks: {detail.assignment.max_marks}
              </Badge>
            </div>
            <h1 className="mt-1.5 text-2xl font-bold text-slate-900">
              {detail.assignment.title}
            </h1>
            {detail.instructions_md ? (
              <p className="mt-1 text-sm text-slate-600">
                {detail.instructions_md}
              </p>
            ) : null}
          </div>

          <div className="text-right text-xs text-slate-500">
            <p className="inline-flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              Due:{" "}
              {detail.assignment.due_at
                ? formatUtcDateTime(detail.assignment.due_at)
                : "No deadline"}
            </p>
            <p className="mt-0.5">
              {detail.assignment.allow_ai_hints
                ? `AI Mentor Hints Allowed (Limit: ${detail.assignment.hint_limit})`
                : "Independent Mode (0 AI Hints)"}
            </p>
          </div>
        </div>

        {/* Released Grade & Teacher Feedback Banner */}
        {detail.grade || detail.feedback.length > 0 ? (
          <div className="mt-4 rounded-xl border border-teal-200 bg-teal-50/60 p-4 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="flex items-center gap-1.5 font-bold text-teal-950">
                <ShieldCheck className="h-4 w-4 text-teal-700" />
                <span>
                  {detail.grade
                    ? `Instructor Grade (${detail.grade.status}): ${detail.grade.marks_awarded} / ${detail.grade.max_marks}`
                    : "Instructor Feedback"}
                </span>
              </p>
              {detail.grade ? (
                <span className="text-slate-600">
                  Graded by {detail.grade.graded_by_name}
                </span>
              ) : null}
            </div>
            {detail.feedback.length > 0 ? (
              <div className="mt-2.5 space-y-1.5">
                {detail.feedback.map((f) => (
                  <div
                    key={f.id}
                    className="rounded-lg border border-teal-200/80 bg-white p-2.5 text-slate-800"
                  >
                    <span className="font-semibold text-indigo-800">
                      [{f.feedback_type}] {f.teacher_name}:
                    </span>{" "}
                    {f.body_md}
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {!detail.can_submit && detail.submit_block_reason ? (
          <div
            role="alert"
            className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-xs font-medium text-amber-900"
          >
            Submission locked: {detail.submit_block_reason}
          </div>
        ) : null}

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

      {/* Problem Tabs (if multi-problem) + Monaco Assignment Workspace */}
      {detail.problems.length > 1 ? (
        <div className="flex flex-wrap gap-2">
          {detail.problems.map((p) => (
            <button
              key={p.link_id}
              type="button"
              onClick={() => setActiveProblemId(p.problem_id)}
              className={`rounded-xl px-3.5 py-2 text-xs font-semibold transition ${
                activeProblemId === p.problem_id
                  ? "bg-indigo-600 text-white"
                  : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              #{p.ordinal} {p.title} ({p.points} pts)
            </button>
          ))}
        </div>
      ) : null}

      {activeProblem ? (
        <section className="grid gap-6 lg:grid-cols-12">
          {/* Left: Problem Statement & Public Examples */}
          <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-bold text-slate-900">
                {activeProblem.title}
              </h2>
              <Badge variant="indigo">
                {activeProblem.mode} · {activeProblem.difficulty}
              </Badge>
            </div>
            <div className="whitespace-pre-wrap text-xs leading-relaxed text-slate-700">
              {activeProblem.statement_md}
            </div>

            {activeProblem.examples.length > 0 ? (
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Public Examples
                </h3>
                {activeProblem.examples.map((ex, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl border border-slate-200 bg-slate-50 p-3 font-mono text-xs"
                  >
                    <p className="text-[11px] font-semibold text-slate-500">
                      Input:
                    </p>
                    <pre className="text-slate-800">{ex.input}</pre>
                    <p className="mt-1 text-[11px] font-semibold text-slate-500">
                      Expected Output:
                    </p>
                    <pre className="text-slate-800">{ex.output}</pre>
                  </div>
                ))}
              </div>
            ) : null}
          </div>

          {/* Right: Monaco Editor + Judge0 Run/Submit + Attempt History */}
          <div className="space-y-4 lg:col-span-7">
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-900 px-4 py-2.5 text-xs text-white">
                <span className="font-semibold">Python 3 · Monaco Workspace</span>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    disabled={savingRevision}
                    onClick={() => void handleSaveRevision()}
                    className="rounded border border-slate-700 px-2.5 py-1 text-slate-300 hover:bg-slate-800"
                  >
                    {savingRevision ? "Saving..." : "Save Draft"}
                  </button>
                  <button
                    type="button"
                    disabled={runningJudge0}
                    onClick={() => void handleRunPublicTests()}
                    className="inline-flex items-center gap-1 rounded-lg bg-slate-700 px-3 py-1.5 font-semibold text-white hover:bg-slate-600"
                  >
                    {runningJudge0 ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Play className="h-3.5 w-3.5" />
                    )}
                    <span>Run Public Tests</span>
                  </button>
                  <button
                    type="button"
                    disabled={!detail.can_submit || submittingAttempt}
                    onClick={() => void handleSubmitAssignment()}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-3.5 py-1.5 font-semibold text-white hover:bg-teal-500 disabled:opacity-50"
                  >
                    {submittingAttempt ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Send className="h-3.5 w-3.5" />
                    )}
                    <span>Submit Assignment to Judge0</span>
                  </button>
                </div>
              </div>

              <CodeEditor
                language="python"
                value={currentCode}
                onChange={(val) =>
                  setCodeByProblem((prev) => ({
                    ...prev,
                    [activeProblemId]: val,
                  }))
                }
                usePlainTextarea={usePlainEditor}
              />

              <div className="border-t border-slate-200 p-3">
                <label
                  htmlFor="assignment-student-notes"
                  className="block text-xs font-semibold text-slate-700"
                >
                  Notes / Explanation for Teacher (Optional)
                </label>
                <input
                  id="assignment-student-notes"
                  type="text"
                  value={studentNotes}
                  onChange={(e) => setStudentNotes(e.target.value)}
                  placeholder="Describe your approach or how you resolved the teacher's revision request..."
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900"
                />
              </div>
            </div>

            {lastAttempt ? (
              <div
                role="status"
                className="rounded-xl border border-teal-200 bg-teal-50 p-3.5 text-xs text-teal-950"
              >
                <p className="flex items-center gap-1.5 font-bold">
                  <CheckCircle2 className="h-4 w-4 text-teal-700" />
                  <span>
                    Assignment Attempt #{lastAttempt.attempt_number} Recorded —
                    Judge0 Verdict: {lastAttempt.verdict} (
                    {lastAttempt.passed_tests}/{lastAttempt.total_tests} tests
                    passed)
                  </span>
                </p>
              </div>
            ) : null}

            {lastRunResult ? (
              <div className="rounded-xl border border-slate-200 bg-white p-3.5 text-xs">
                <p className="font-bold text-slate-900">
                  Public Test Run: {lastRunResult.verdict} (
                  {lastRunResult.passed_tests} / {lastRunResult.total_tests}{" "}
                  public tests passed)
                </p>
              </div>
            ) : null}

            {/* Persisted Assignment Attempts History */}
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Submitted Assignment Attempts ({detail.attempts.length})
              </h3>
              <div className="mt-2.5 space-y-2 text-xs">
                {detail.attempts.length === 0 ? (
                  <p className="text-slate-500">
                    No assignment attempts submitted yet.
                  </p>
                ) : (
                  detail.attempts.map((att) => (
                    <div
                      key={att.id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-bold text-slate-900">
                          Attempt #{att.attempt_number}
                        </span>
                        <Badge
                          variant={
                            att.verdict === "accepted" ? "teal" : "amber"
                          }
                        >
                          {att.verdict} ({att.passed_tests}/{att.total_tests})
                        </Badge>
                        {att.is_late ? (
                          <Badge variant="amber">Late</Badge>
                        ) : null}
                      </div>
                      <span className="text-[11px] text-slate-500">
                        {formatUtcDateTime(att.submitted_at)}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}
