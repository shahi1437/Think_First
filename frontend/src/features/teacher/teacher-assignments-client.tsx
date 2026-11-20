"use client";

import {
  AlertCircle,
  Archive,
  ArrowRight,
  CheckCircle2,
  Loader2,
  Plus,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  archiveTeacherAssignment,
  createTeacherAssignment,
  publishTeacherAssignment,
} from "@/lib/api-client";
import type {
  AssignmentSummaryView,
  CourseSummaryView,
} from "@/types/classroom";
import type { StudentProblemListItem } from "@/types/problems";

interface TeacherAssignmentsClientProps {
  accessToken: string;
  initialClasses: CourseSummaryView[];
  initialAssignments: AssignmentSummaryView[];
  publishedProblems: StudentProblemListItem[];
}

export function TeacherAssignmentsClient({
  accessToken,
  initialClasses,
  initialAssignments,
  publishedProblems,
}: TeacherAssignmentsClientProps) {
  const activeClasses = initialClasses.filter((c) => c.status === "active");
  const [assignments, setAssignments] =
    useState<AssignmentSummaryView[]>(initialAssignments);
  const [courseId, setCourseId] = useState(activeClasses[0]?.id ?? "");
  const [title, setTitle] = useState("");
  const [instructions, setInstructions] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [maxMarks, setMaxMarks] = useState("50");
  const [maxAttempts, setMaxAttempts] = useState("3");
  const [allowHints, setAllowHints] = useState(true);
  const [hintLimit, setHintLimit] = useState("2");
  const [allowLate, setAllowLate] = useState(false);
  const [allowResubmit, setAllowResubmit] = useState(true);
  const [selectedProblemIds, setSelectedProblemIds] = useState<string[]>(() => {
    const preferred =
      publishedProblems.find((p) => p.slug === "debug-inclusive-range-sum") ??
      publishedProblems[0];
    return preferred ? [preferred.problem_id] : [];
  });
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function toggleProblem(problemId: string) {
    setSelectedProblemIds((prev) =>
      prev.includes(problemId)
        ? prev.filter((id) => id !== problemId)
        : [...prev, problemId],
    );
  }

  async function handleCreate(publishNow: boolean) {
    if (!courseId) {
      setError("Please create or select an active class first.");
      return;
    }
    if (selectedProblemIds.length === 0) {
      setError("Please select at least one approved problem.");
      return;
    }
    setError(null);
    setCreating(true);
    try {
      const totalMarks = Math.max(1, Number(maxMarks) || 100);
      const perProblemPts = Number(
        (totalMarks / selectedProblemIds.length).toFixed(2),
      );
      const created = await createTeacherAssignment(accessToken, {
        course_id: courseId,
        title: title.trim(),
        instructions_md: instructions.trim(),
        due_at: dueDate ? new Date(dueDate).toISOString() : null,
        max_marks: totalMarks,
        grading_policy: "judge0_assisted_manual",
        max_attempts: Math.max(1, Number(maxAttempts) || 3),
        allow_ai_hints: allowHints,
        hint_limit: allowHints ? Math.min(3, Math.max(0, Number(hintLimit))) : 0,
        allow_late_submissions: allowLate,
        allow_resubmission_on_revision: allowResubmit,
        publish_now: publishNow,
        problems: selectedProblemIds.map((pid) => ({
          problem_id: pid,
          points: perProblemPts,
        })),
      });
      setAssignments((prev) => [created, ...prev]);
      setTitle("");
      setInstructions("");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not create assignment.",
      );
    } finally {
      setCreating(false);
    }
  }

  async function handlePublish(id: string) {
    setError(null);
    setBusyId(id);
    try {
      const updated = await publishTeacherAssignment(accessToken, id);
      setAssignments((prev) =>
        prev.map((a) => (a.id === updated.id ? updated : a)),
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not publish assignment.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function handleArchive(id: string) {
    setError(null);
    setBusyId(id);
    try {
      const updated = await archiveTeacherAssignment(accessToken, id);
      setAssignments((prev) =>
        prev.map((a) => (a.id === updated.id ? updated : a)),
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not archive assignment.",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
              Assignment Authoring &amp; Publishing
            </p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900">
              Assignments &amp; Grading
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Assign Admin-approved published problems with server-enforced
              deadlines, attempt limits, and AI hint policies.
            </p>
          </div>
          <Link
            href="/teacher/classes"
            className="rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            My Classes
          </Link>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            void handleCreate(true);
          }}
          className="mt-5 space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4"
        >
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label
                htmlFor="asg-class"
                className="block text-xs font-semibold text-slate-700"
              >
                Target Class
              </label>
              <select
                id="asg-class"
                value={courseId}
                onChange={(e) => setCourseId(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-xs text-slate-900"
              >
                {activeClasses.length === 0 ? (
                  <option value="">No active classes</option>
                ) : (
                  activeClasses.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.code} — {c.title}
                    </option>
                  ))
                )}
              </select>
            </div>

            <div className="sm:col-span-2">
              <label
                htmlFor="asg-title"
                className="block text-xs font-semibold text-slate-700"
              >
                Assignment Title
              </label>
              <input
                id="asg-title"
                type="text"
                required
                minLength={3}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Lab 1: Loop Boundary Debugging"
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900"
              />
            </div>

            <div>
              <label
                htmlFor="asg-due"
                className="block text-xs font-semibold text-slate-700"
              >
                Due Date (Optional)
              </label>
              <input
                id="asg-due"
                type="datetime-local"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-xs text-slate-900"
              />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label
                htmlFor="asg-marks"
                className="block text-xs font-semibold text-slate-700"
              >
                Max Marks
              </label>
              <input
                id="asg-marks"
                type="number"
                min={1}
                max={1000}
                value={maxMarks}
                onChange={(e) => setMaxMarks(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900"
              />
            </div>

            <div>
              <label
                htmlFor="asg-attempts"
                className="block text-xs font-semibold text-slate-700"
              >
                Allowed Attempts
              </label>
              <input
                id="asg-attempts"
                type="number"
                min={1}
                max={50}
                value={maxAttempts}
                onChange={(e) => setMaxAttempts(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900"
              />
            </div>

            <div>
              <label
                htmlFor="asg-hints"
                className="block text-xs font-semibold text-slate-700"
              >
                AI Hint Limit (0-3)
              </label>
              <input
                id="asg-hints"
                type="number"
                min={0}
                max={3}
                disabled={!allowHints}
                value={hintLimit}
                onChange={(e) => setHintLimit(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 disabled:bg-slate-100"
              />
            </div>

            <div className="flex flex-col justify-center gap-1.5 pt-3 text-xs text-slate-700">
              <label className="inline-flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={allowHints}
                  onChange={(e) => setAllowHints(e.target.checked)}
                />
                <span>Allow Socratic AI hints</span>
              </label>
              <label className="inline-flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={allowLate}
                  onChange={(e) => setAllowLate(e.target.checked)}
                />
                <span>Allow late submissions</span>
              </label>
              <label className="inline-flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={allowResubmit}
                  onChange={(e) => setAllowResubmit(e.target.checked)}
                />
                <span>Allow resubmit on revision</span>
              </label>
            </div>
          </div>

          <div>
            <label
              htmlFor="asg-instructions"
              className="block text-xs font-semibold text-slate-700"
            >
              Instructions
            </label>
            <textarea
              id="asg-instructions"
              rows={2}
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="Explain grading rubric, edge cases to test, and hint policy..."
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2.5 text-xs text-slate-900"
            />
          </div>

          <div>
            <p className="text-xs font-semibold text-slate-700">
              Select Admin-Approved Published Problems (
              {selectedProblemIds.length} selected)
            </p>
            <div className="mt-1.5 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {publishedProblems.map((prob) => {
                const checked = selectedProblemIds.includes(prob.problem_id);
                return (
                  <label
                    key={prob.problem_id}
                    className={`flex cursor-pointer items-start gap-2 rounded-xl border p-2.5 text-xs transition ${
                      checked
                        ? "border-indigo-600 bg-indigo-50/60"
                        : "border-slate-200 bg-white"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleProblem(prob.problem_id)}
                      className="mt-0.5"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-bold text-slate-900">
                        {prob.title}
                      </p>
                      <p className="text-[11px] text-slate-500">
                        {prob.mode} · {prob.difficulty}
                      </p>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>

          <div className="flex flex-wrap justify-end gap-2">
            <button
              type="button"
              disabled={creating || !title.trim()}
              onClick={() => void handleCreate(false)}
              className="rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60"
            >
              Save as Draft
            </button>
            <button
              type="submit"
              disabled={creating || !title.trim()}
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
            >
              {creating ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Plus className="h-3.5 w-3.5" />
              )}
              <span>Publish Assignment Now</span>
            </button>
          </div>
        </form>

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

      {/* Assignments Table */}
      <section aria-label="Teacher assignments list" className="space-y-3">
        {assignments.map((a) => (
          <article
            key={a.id}
            className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded bg-indigo-100 px-2 py-0.5 font-mono text-xs font-bold text-indigo-900">
                  {a.course_code}
                </span>
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
                <Badge variant="indigo">
                  {a.submitted_count}/{a.enrolled_students_count} submitted ·{" "}
                  {a.pending_grading_count} pending grade
                </Badge>
              </div>
              <h2 className="mt-1.5 text-base font-bold text-slate-900">
                {a.title}
              </h2>
              <p className="mt-0.5 text-xs text-slate-600">
                Max Marks: {a.max_marks} · Max Attempts: {a.max_attempts} ·{" "}
                {a.problem_count} problem(s) ·{" "}
                {a.allow_ai_hints
                  ? `${a.hint_limit} AI hint(s) allowed`
                  : "No AI hints"}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {a.status === "draft" ? (
                <button
                  type="button"
                  disabled={busyId === a.id}
                  onClick={() => void handlePublish(a.id)}
                  className="inline-flex items-center gap-1 rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-teal-500"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>Publish</span>
                </button>
              ) : null}
              {a.status !== "archived" ? (
                <button
                  type="button"
                  disabled={busyId === a.id}
                  onClick={() => void handleArchive(a.id)}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  <Archive className="h-3.5 w-3.5" />
                  <span>Archive</span>
                </button>
              ) : null}
              <Link
                href={`/teacher/assignments/${a.id}`}
                className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-700"
              >
                <span>Review &amp; Grade</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
