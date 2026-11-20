"use client";

import {
  AlertCircle,
  ArrowRight,
  BookOpen,
  KeyRound,
  Loader2,
  LogOut,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { joinStudentClass, leaveStudentClass } from "@/lib/api-client";
import type { StudentEnrolledCourseView } from "@/types/classroom";

interface StudentClassesClientProps {
  accessToken: string;
  initialClasses: StudentEnrolledCourseView[];
}

export function StudentClassesClient({
  accessToken,
  initialClasses,
}: StudentClassesClientProps) {
  const [classes, setClasses] =
    useState<StudentEnrolledCourseView[]>(initialClasses);
  const [inviteCode, setInviteCode] = useState("");
  const [joining, setJoining] = useState(false);
  const [leavingId, setLeavingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleJoinClass(e: React.FormEvent) {
    e.preventDefault();
    if (!inviteCode.trim()) return;
    setError(null);
    setJoining(true);
    try {
      const joined = await joinStudentClass(accessToken, inviteCode.trim());
      setClasses((prev) => [
        joined,
        ...prev.filter((c) => c.course_id !== joined.course_id),
      ]);
      setInviteCode("");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not join class with code.",
      );
    } finally {
      setJoining(false);
    }
  }

  async function handleLeave(courseId: string) {
    setError(null);
    setLeavingId(courseId);
    try {
      await leaveStudentClass(accessToken, courseId);
      setClasses((prev) => prev.filter((c) => c.course_id !== courseId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not leave class.");
    } finally {
      setLeavingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-teal-700">
              Classroom Enrollment
            </p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900">
              My Classes
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Enter your instructor&apos;s invitation code (e.g.{" "}
              <code className="font-mono text-xs">CM-XXXXX-XXXXX</code>) to
              enroll and access class assignments.
            </p>
          </div>
          <Link
            href="/student/assignments"
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-indigo-500"
          >
            <span>My Assignments</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        <form
          onSubmit={(e) => void handleJoinClass(e)}
          className="mt-5 flex flex-wrap gap-2 rounded-xl border border-slate-200 bg-slate-50 p-4"
        >
          <div className="relative min-w-0 flex-1">
            <KeyRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              required
              minLength={6}
              maxLength={40}
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
              aria-label="Class invitation code"
              placeholder="Enter invitation code (e.g. CM-ABCDE-12345)"
              className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 font-mono text-xs uppercase text-slate-900"
            />
          </div>
          <button
            type="submit"
            disabled={joining}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-60"
          >
            {joining ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            <span>Join Class</span>
          </button>
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

      <section aria-label="Enrolled classes" className="grid gap-4 md:grid-cols-2">
        {classes.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-xs text-slate-500 md:col-span-2">
            You have not joined any classes yet. Enter a class invitation code
            above to enroll.
          </div>
        ) : (
          classes.map((c) => (
            <article
              key={c.membership_id}
              className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="rounded bg-indigo-100 px-2 py-0.5 font-mono text-xs font-bold text-indigo-900">
                    {c.code}
                  </span>
                  <Badge
                    variant={
                      c.membership_status === "active" ? "teal" : "amber"
                    }
                  >
                    {c.membership_status}
                  </Badge>
                </div>
                <h2 className="mt-2 text-base font-bold text-slate-900">
                  {c.title}
                </h2>
                <p className="mt-0.5 text-xs text-slate-500">
                  Instructor: {c.teacher_name} {c.term ? `· ${c.term}` : ""}
                </p>
                <p className="mt-2 text-xs text-slate-600">
                  {c.description || "No class description."}
                </p>
              </div>

              <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-600">
                  <BookOpen className="h-3.5 w-3.5 text-indigo-600" />
                  {c.published_assignments_count} published assignment(s)
                </span>

                <div className="flex items-center gap-2">
                  {c.allow_student_leave ? (
                    <button
                      type="button"
                      disabled={leavingId === c.course_id}
                      onClick={() => void handleLeave(c.course_id)}
                      className="inline-flex items-center gap-1 rounded-lg border border-rose-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                      <span>Leave</span>
                    </button>
                  ) : null}
                  <Link
                    href="/student/assignments"
                    className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-700"
                  >
                    <span>Assignments</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            </article>
          ))
        )}
      </section>
    </div>
  );
}
