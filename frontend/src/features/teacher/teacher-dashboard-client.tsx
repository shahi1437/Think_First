"use client";

import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  BookOpen,
  Calendar,
  CheckCircle2,
  ClipboardList,
  GraduationCap,
  Sparkles,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import type { TeacherDashboardView } from "@/types/classroom";

interface TeacherDashboardClientProps {
  teacherName: string;
  initialDashboard: TeacherDashboardView;
  initialLanguage?: "en" | "bn";
}

export function TeacherDashboardClient({
  teacherName,
  initialDashboard,
  initialLanguage = "en",
}: TeacherDashboardClientProps) {
  const [lang, setLang] = useState<"en" | "bn">(initialLanguage);
  const isBn = lang === "bn";
  const { analytics } = initialDashboard;

  return (
    <div className="space-y-6" lang={lang}>
      <section className="tf-animate-enter rounded-2xl border border-slate-800 bg-gradient-to-br from-[#0b1221] via-[#111b31] to-[#0f172a] p-6 text-white shadow-md sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-teal-300">
              <GraduationCap className="h-4 w-4" aria-hidden="true" />
              <span>
                {isBn
                  ? "শিক্ষক ড্যাশবোর্ড ও ক্লাসরুম অ্যানালিটিক্স"
                  : "Authorized Teacher Dashboard & Classroom Analytics"}
              </span>
            </p>
            <h1 className="mt-1.5 text-3xl font-bold tracking-tight text-white sm:text-[34px]">
              {isBn ? `স্বাগতম, ${teacherName}` : `Welcome, ${teacherName}`}
            </h1>
            <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-300">
              {initialDashboard.methodology_note}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <div
              role="group"
              aria-label="Teacher dashboard language"
              className="inline-flex rounded-xl border border-slate-700 bg-slate-900/90 p-1 text-sm"
            >
              <button
                type="button"
                onClick={() => setLang("en")}
                aria-pressed={lang === "en"}
                className={`rounded-lg px-3 py-1.5 font-semibold transition ${
                  lang === "en"
                    ? "bg-teal-400 text-slate-950"
                    : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                English
              </button>
              <button
                type="button"
                onClick={() => setLang("bn")}
                aria-pressed={lang === "bn"}
                className={`rounded-lg px-3 py-1.5 font-semibold transition ${
                  lang === "bn"
                    ? "bg-teal-400 text-slate-950"
                    : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                বাংলা
              </button>
            </div>

            <Link
              href="/teacher/classes"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-600 bg-slate-900/70 px-4 py-2.5 text-[15px] font-semibold text-white transition hover:bg-slate-800"
            >
              <Users className="h-4 w-4" aria-hidden="true" />
              <span>{isBn ? "ক্লাস পরিচালনা" : "Manage Classes"}</span>
            </Link>
            <Link
              href="/teacher/assignments"
              className="inline-flex items-center gap-2 rounded-xl bg-teal-400 px-4 py-2.5 text-[15px] font-semibold text-slate-950 transition hover:bg-teal-300"
            >
              <ClipboardList className="h-4 w-4" aria-hidden="true" />
              <span>{isBn ? "অ্যাসাইনমেন্ট ও গ্রেডিং" : "Assignments & Grading"}</span>
            </Link>
          </div>
        </div>

        {/* Real Aggregated Stat Counters */}
        <div className="mt-6 grid gap-3.5 sm:grid-cols-2 lg:grid-cols-5">
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 p-4">
            <p className="text-xs font-semibold uppercase text-slate-400">
              {isBn ? "সক্রিয় ক্লাস" : "Active Classes"}
            </p>
            <p className="mt-1.5 text-2xl font-bold text-white">
              {initialDashboard.active_courses_count} /{" "}
              {initialDashboard.courses_count}
            </p>
          </div>
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 p-4">
            <p className="text-xs font-semibold uppercase text-slate-400">
              {isBn ? "ভর্তিকৃত শিক্ষার্থী" : "Enrolled Students"}
            </p>
            <p className="mt-1.5 text-2xl font-bold text-teal-300">
              {initialDashboard.total_enrolled_students}
            </p>
          </div>
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 p-4">
            <p className="text-xs font-semibold uppercase text-slate-400">
              {isBn ? "চলমান অ্যাসাইনমেন্ট" : "Active Assignments"}
            </p>
            <p className="mt-1.5 text-2xl font-bold text-white">
              {initialDashboard.active_assignments_count}
            </p>
          </div>
          <div className="rounded-xl border border-amber-400/30 bg-amber-500/10 p-4">
            <p className="text-xs font-semibold uppercase text-amber-200">
              {isBn ? "গ্রেডিং বাকি" : "Pending Grading"}
            </p>
            <p className="mt-1.5 text-2xl font-bold text-amber-300">
              {initialDashboard.pending_grading_count}
            </p>
          </div>
          <div className="rounded-xl border border-teal-400/30 bg-teal-500/10 p-4">
            <p className="text-xs font-semibold uppercase text-teal-200">
              {isBn ? "গ্রেড প্রকাশিত" : "Graded Submissions"}
            </p>
            <p className="mt-1.5 text-2xl font-bold text-teal-300">
              {initialDashboard.graded_submissions_count}
            </p>
          </div>
        </div>
      </section>

      {initialDashboard.pending_grading_count > 0 ? (
        <section
          aria-label="Submissions awaiting review"
          className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-950"
        >
          <div className="flex items-center gap-2.5">
            <ClipboardList className="h-5 w-5 text-amber-700" aria-hidden="true" />
            <span>
              <strong>{initialDashboard.pending_grading_count}</strong> student
              submission(s) awaiting review and grading.
            </span>
          </div>
          <Link
            href="/teacher/assignments"
            className="inline-flex items-center gap-1.5 rounded-lg bg-amber-700 px-3.5 py-1.5 text-xs font-semibold text-white transition hover:bg-amber-800"
          >
            <span>Review Submissions</span>
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </section>
      ) : null}

      {/* Classes Taught & Upcoming Deadlines */}
      <section className="grid gap-6 lg:grid-cols-12">
        <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-7">
          <div className="flex items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <BookOpen className="h-4 w-4 text-indigo-600" aria-hidden="true" />
              <span>{isBn ? "আমার ক্লাসসমূহ" : "Classes Taught"}</span>
            </h2>
            <Link
              href="/teacher/classes"
              className="text-xs font-semibold text-indigo-700 hover:underline"
            >
              {isBn ? "+ নতুন ক্লাস তৈরি করো" : "+ Create Class"}
            </Link>
          </div>

          {initialDashboard.courses.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500">
              No classes created yet. Open Manage Classes to create your first course and generate a join code.
            </p>
          ) : (
            <div className="space-y-2.5">
              {initialDashboard.courses.map((c) => (
                <div
                  key={c.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3.5"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded bg-indigo-100 px-2 py-0.5 font-mono text-xs font-bold text-indigo-900">
                        {c.code}
                      </span>
                      <Badge variant={c.status === "active" ? "teal" : "neutral"}>
                        {c.status}
                      </Badge>
                      {c.term ? (
                        <span className="text-xs text-slate-500">{c.term}</span>
                      ) : null}
                    </div>
                    <h3 className="mt-1 text-sm font-bold text-slate-900">
                      {c.title}
                    </h3>
                    <p className="text-xs text-slate-600">
                      {c.active_students_count} active student(s) ·{" "}
                      {c.pending_students_count} pending · {c.assignments_count}{" "}
                      assignment(s)
                    </p>
                  </div>
                  <Link
                    href={`/teacher/classes/${c.id}`}
                    className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-700"
                  >
                    <span>{isBn ? "বিস্তারিত" : "Open Class"}</span>
                    <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-5">
          <div className="flex items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <Calendar className="h-4 w-4 text-teal-600" aria-hidden="true" />
              <span>{isBn ? "আসন্ন ডেডলাইন" : "Upcoming Deadlines"}</span>
            </h2>
            <Link
              href="/teacher/assignments"
              className="text-xs font-semibold text-indigo-700 hover:underline"
            >
              {isBn ? "সব দেখো" : "All Assignments"}
            </Link>
          </div>

          {initialDashboard.upcoming_deadlines.length === 0 ? (
            <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-xs text-slate-500">
              No upcoming assignment deadlines scheduled.
            </p>
          ) : (
            <div className="space-y-2.5">
              {initialDashboard.upcoming_deadlines.map((a) => (
                <Link
                  key={a.id}
                  href={`/teacher/assignments/${a.id}`}
                  className="block rounded-xl border border-slate-200 bg-slate-50 p-3.5 transition hover:border-indigo-300"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-xs font-semibold text-indigo-700">
                      {a.course_code}
                    </span>
                    <Badge
                      variant={a.pending_grading_count > 0 ? "amber" : "teal"}
                    >
                      {a.submitted_count}/{a.enrolled_students_count} submitted ·{" "}
                      {a.pending_grading_count} to grade
                    </Badge>
                  </div>
                  <p className="mt-1 text-sm font-bold text-slate-900">
                    {a.title}
                  </p>
                  <p className="mt-0.5 text-[11px] text-slate-500">
                    Due:{" "}
                    {a.due_at ? new Date(a.due_at).toLocaleString() : "No due date"}
                  </p>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Evidence-Based Class Analytics */}
      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <BarChart3 className="h-4 w-4 text-teal-600" aria-hidden="true" />
            <span>{isBn ? "Judge0 ফলাফল প্রবণতা" : "Real Judge0 Verdict Trends"}</span>
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            {analytics.accepted_attempts} accepted / {analytics.total_attempts}{" "}
            total attempts
          </p>
          <div className="mt-3 space-y-1.5 text-xs">
            {analytics.verdict_breakdown.length === 0 ? (
              <p className="text-slate-500">No Judge0 assignment attempts yet.</p>
            ) : (
              analytics.verdict_breakdown.map((v) => (
                <div
                  key={v.verdict}
                  className="flex items-center justify-between rounded-lg bg-slate-50 px-2.5 py-1.5"
                >
                  <span className="font-mono font-medium text-slate-700">
                    {v.verdict}
                  </span>
                  <span className="font-bold text-slate-900">{v.count}</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <Sparkles className="h-4 w-4 text-indigo-600" aria-hidden="true" />
            <span>
              {isBn ? "সাধারণ প্রোগ্রামিং ভুল (ML)" : "Common ML Misconceptions"}
            </span>
          </h2>
          <div className="mt-3 space-y-1.5 text-xs">
            {analytics.common_misconceptions.length === 0 ? (
              <p className="text-slate-500">
                No ML error diagnoses recorded for enrolled students yet.
              </p>
            ) : (
              analytics.common_misconceptions.map((m) => (
                <div
                  key={m.error_code}
                  className="flex items-center justify-between rounded-lg bg-slate-50 px-2.5 py-1.5"
                >
                  <span className="font-mono text-slate-700">{m.error_code}</span>
                  <Badge variant="amber">{m.occurrences}</Badge>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <CheckCircle2 className="h-4 w-4 text-teal-600" aria-hidden="true" />
            <span>
              {isBn ? "ক্লাস স্কিল গ্যাপ ও হিন্ট" : "Class Skill Gaps & Hint Reliance"}
            </span>
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            {analytics.total_hints_used} AI hints used ·{" "}
            {analytics.verified_independent_transfers} independent transfers
          </p>
          <div className="mt-3 space-y-1.5 text-xs">
            {analytics.skill_gaps.length === 0 ? (
              <p className="text-slate-500">
                No Skill Graph observations recorded for enrolled students yet.
              </p>
            ) : (
              analytics.skill_gaps.slice(0, 5).map((g) => (
                <div
                  key={g.skill_slug}
                  className="flex items-center justify-between rounded-lg bg-slate-50 px-2.5 py-1.5"
                >
                  <span className="font-mono text-slate-700">{g.skill_slug}</span>
                  <span className="text-slate-600">
                    {g.unobserved_or_guided_count} gap / {g.verified_count} verified
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <AlertTriangle className="h-4 w-4 text-amber-600" aria-hidden="true" />
            <span>
              {isBn ? "অতিরিক্ত সহায়তা প্রয়োজন" : "Students Needing Support"}
            </span>
          </h2>
          <div className="mt-3 space-y-2 text-xs">
            {analytics.students_needing_support.length === 0 ? (
              <p className="text-slate-500">
                No students currently flagged with repeated failed attempts.
              </p>
            ) : (
              analytics.students_needing_support.map((s) => (
                <div
                  key={s.student_id}
                  className="rounded-lg border border-amber-200 bg-amber-50/60 p-2.5"
                >
                  <p className="font-bold text-slate-900">{s.full_name}</p>
                  <p className="text-[11px] text-slate-600">{s.reason}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
