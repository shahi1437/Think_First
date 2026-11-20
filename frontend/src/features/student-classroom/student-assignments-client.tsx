"use client";

import {
  ArrowRight,
  Calendar,
  CheckCircle2,
  ClipboardList,
  Loader2,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { fetchStudentAssignments } from "@/lib/api-client";
import type {
  StudentAssignmentFilter,
  StudentAssignmentListItemView,
} from "@/types/classroom";

interface StudentAssignmentsClientProps {
  accessToken: string;
  initialAssignments: StudentAssignmentListItemView[];
}

const FILTERS: Array<{ value: StudentAssignmentFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "submitted", label: "Submitted" },
  { value: "revision_requested", label: "Revision Requested" },
  { value: "graded", label: "Graded" },
  { value: "overdue", label: "Overdue" },
];

export function StudentAssignmentsClient({
  accessToken,
  initialAssignments,
}: StudentAssignmentsClientProps) {
  const [assignments, setAssignments] =
    useState<StudentAssignmentListItemView[]>(initialAssignments);
  const [filter, setFilter] = useState<StudentAssignmentFilter>("all");
  const [loading, setLoading] = useState(false);

  async function handleFilter(next: StudentAssignmentFilter) {
    setFilter(next);
    setLoading(true);
    try {
      const list = await fetchStudentAssignments(accessToken, next);
      setAssignments(list);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-700">
              <ClipboardList className="h-3.5 w-3.5" />
              <span>Class Assignments &amp; Judge0 Evaluation</span>
            </p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900">
              My Assignments
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Solve assigned problems in the Monaco Editor, run real Judge0
              tests, and review instructor grades and feedback.
            </p>
          </div>
          <Link
            href="/student/classes"
            className="rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            My Classes
          </Link>
        </div>

        <div
          role="group"
          aria-label="Filter assignments"
          className="mt-5 flex flex-wrap gap-1.5"
        >
          {FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              aria-pressed={filter === f.value}
              onClick={() => void handleFilter(f.value)}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                filter === f.value
                  ? "bg-indigo-600 text-white"
                  : "border border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
              }`}
            >
              {f.label}
            </button>
          ))}
          {loading ? (
            <Loader2 className="ml-2 h-4 w-4 animate-spin text-indigo-600" />
          ) : null}
        </div>
      </section>

      <section aria-label="Student assignments list" className="space-y-3">
        {assignments.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-xs text-slate-500">
            No assignments match this filter. Join a class in My Classes or
            switch filters above.
          </div>
        ) : (
          assignments.map((a) => (
            <article
              key={a.assignment_id}
              className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded bg-indigo-100 px-2 py-0.5 font-mono text-xs font-bold text-indigo-900">
                    {a.course_code}
                  </span>
                  <Badge
                    variant={
                      a.workflow_status === "graded"
                        ? "teal"
                        : a.workflow_status === "revision_requested"
                          ? "amber"
                          : a.is_overdue
                            ? "amber"
                            : "indigo"
                    }
                  >
                    {a.workflow_status.replaceAll("_", " ")}
                  </Badge>
                  <Badge variant="neutral">
                    Attempts: {a.attempts_used} / {a.max_attempts}
                  </Badge>
                  {a.released_marks !== null &&
                  a.released_marks !== undefined ? (
                    <Badge variant="teal">
                      <CheckCircle2 className="h-3 w-3" />
                      <span>
                        Grade: {a.released_marks} / {a.max_marks}
                      </span>
                    </Badge>
                  ) : (
                    <Badge variant="neutral">Max Marks: {a.max_marks}</Badge>
                  )}
                </div>

                <h2 className="mt-2 text-base font-bold text-slate-900">
                  {a.title}
                </h2>
                <p className="mt-1 inline-flex items-center gap-1.5 text-xs text-slate-500">
                  <Calendar className="h-3.5 w-3.5" />
                  <span>
                    Due:{" "}
                    {a.due_at
                      ? new Date(a.due_at).toLocaleString()
                      : "No deadline"}{" "}
                    · {a.problem_count} problem(s) ·{" "}
                    {a.allow_ai_hints
                      ? `Up to ${a.hint_limit} AI hint(s)`
                      : "AI hints disabled"}
                  </span>
                </p>
              </div>

              <Link
                href={`/student/assignments/${a.assignment_id}`}
                className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500"
              >
                <span>Open Assignment Workspace</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </article>
          ))
        )}
      </section>
    </div>
  );
}
