"use client";

import {
  AlertCircle,
  Archive,
  ArrowRight,
  Loader2,
  Plus,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { archiveTeacherClass, createTeacherClass } from "@/lib/api-client";
import type { CourseSummaryView, EnrollmentPolicy } from "@/types/classroom";

interface TeacherClassesClientProps {
  accessToken: string;
  initialClasses: CourseSummaryView[];
}

export function TeacherClassesClient({
  accessToken,
  initialClasses,
}: TeacherClassesClientProps) {
  const [classes, setClasses] = useState<CourseSummaryView[]>(initialClasses);
  const [code, setCode] = useState("");
  const [title, setTitle] = useState("");
  const [term, setTerm] = useState("Fall 2026");
  const [description, setDescription] = useState("");
  const [enrollmentPolicy, setEnrollmentPolicy] =
    useState<EnrollmentPolicy>("open_with_code");
  const [allowLeave, setAllowLeave] = useState(true);
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleCreateClass(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setCreating(true);
    try {
      const created = await createTeacherClass(accessToken, {
        code: code.trim(),
        title: title.trim(),
        term: term.trim(),
        description: description.trim(),
        enrollment_policy: enrollmentPolicy,
        allow_student_leave: allowLeave,
      });
      setClasses((prev) => [created, ...prev]);
      setCode("");
      setTitle("");
      setDescription("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create class.");
    } finally {
      setCreating(false);
    }
  }

  async function handleToggleArchive(course: CourseSummaryView) {
    setError(null);
    setBusyId(course.id);
    try {
      const updated = await archiveTeacherClass(
        accessToken,
        course.id,
        course.status === "active",
      );
      setClasses((prev) =>
        prev.map((c) => (c.id === updated.id ? updated : c)),
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not update class status.",
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
            <p className="text-xs font-semibold uppercase tracking-wider text-teal-700">
              Classroom &amp; Course Management
            </p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900">
              My Classes
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Create authorized courses, generate high-entropy invitation codes,
              and manage student rosters.
            </p>
          </div>
          <Link
            href="/teacher/assignments"
            className="rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-indigo-500"
          >
            Go to Assignments
          </Link>
        </div>

        <form
          onSubmit={(e) => void handleCreateClass(e)}
          className="mt-5 grid gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          <div>
            <label
              htmlFor="class-code"
              className="block text-xs font-semibold text-slate-700"
            >
              Course Code
            </label>
            <input
              id="class-code"
              type="text"
              required
              minLength={2}
              maxLength={32}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g. CSE101-A"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900"
            />
          </div>

          <div>
            <label
              htmlFor="class-title"
              className="block text-xs font-semibold text-slate-700"
            >
              Class Title
            </label>
            <input
              id="class-title"
              type="text"
              required
              minLength={3}
              maxLength={160}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Structured Programming Lab"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900"
            />
          </div>

          <div>
            <label
              htmlFor="class-term"
              className="block text-xs font-semibold text-slate-700"
            >
              Academic Term
            </label>
            <input
              id="class-term"
              type="text"
              value={term}
              onChange={(e) => setTerm(e.target.value)}
              placeholder="e.g. Fall 2026"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900"
            />
          </div>

          <div className="sm:col-span-2">
            <label
              htmlFor="class-desc"
              className="block text-xs font-semibold text-slate-700"
            >
              Description
            </label>
            <input
              id="class-desc"
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief overview of lab objectives and grading..."
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900"
            />
          </div>

          <div>
            <label
              htmlFor="class-policy"
              className="block text-xs font-semibold text-slate-700"
            >
              Enrollment Policy
            </label>
            <select
              id="class-policy"
              value={enrollmentPolicy}
              onChange={(e) =>
                setEnrollmentPolicy(e.target.value as EnrollmentPolicy)
              }
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900"
            >
              <option value="open_with_code">
                Auto-Enroll with Invite Code
              </option>
              <option value="approval_required">
                Require Teacher Approval
              </option>
            </select>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 sm:col-span-2 lg:col-span-3">
            <label className="inline-flex items-center gap-2 text-xs font-medium text-slate-700">
              <input
                type="checkbox"
                checked={allowLeave}
                onChange={(e) => setAllowLeave(e.target.checked)}
                className="rounded border-slate-300"
              />
              <span>Allow students to leave this class independently</span>
            </label>

            <button
              type="submit"
              disabled={creating}
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
            >
              {creating ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Plus className="h-3.5 w-3.5" />
              )}
              <span>Create Class</span>
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

      <section aria-label="Teacher classes list" className="grid gap-4 md:grid-cols-2">
        {classes.map((c) => (
          <article
            key={c.id}
            className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="rounded bg-indigo-100 px-2 py-0.5 font-mono text-xs font-bold text-indigo-900">
                  {c.code}
                </span>
                <div className="flex items-center gap-1.5">
                  <Badge variant={c.status === "active" ? "teal" : "neutral"}>
                    {c.status}
                  </Badge>
                  <Badge variant="indigo">
                    {c.enrollment_policy === "open_with_code"
                      ? "Invite Code"
                      : "Approval Required"}
                  </Badge>
                </div>
              </div>
              <h2 className="mt-2 text-base font-bold text-slate-900">
                {c.title}
              </h2>
              <p className="mt-1 text-xs text-slate-600">
                {c.description || "No description provided."}
              </p>
              <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-600">
                <span className="inline-flex items-center gap-1 font-semibold">
                  <Users className="h-3.5 w-3.5 text-indigo-600" />
                  {c.active_students_count} active · {c.pending_students_count}{" "}
                  pending
                </span>
                <span>{c.assignments_count} assignment(s)</span>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
              <button
                type="button"
                disabled={busyId === c.id}
                onClick={() => void handleToggleArchive(c)}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                <Archive className="h-3.5 w-3.5" />
                <span>{c.status === "active" ? "Archive" : "Restore"}</span>
              </button>

              <Link
                href={`/teacher/classes/${c.id}`}
                className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-700"
              >
                <span>Manage Class &amp; Roster</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
