"use client";

import {
  Activity,
  BookOpen,
  CheckCircle2,
  ClipboardCheck,
  Database,
  GraduationCap,
  Layers,
  ShieldAlert,
  ShieldCheck,
  Users,
} from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { TeacherManagementSection } from "@/features/admin/teacher-management-section";
import type {
  AdminDashboardOverview,
  AdminOperationsHealth,
  AdminUserSummary,
  TeacherInvitationView,
} from "@/types/admin";

interface AdminDashboardClientProps {
  adminName: string;
  overview: AdminDashboardOverview;
  operationsHealth?: AdminOperationsHealth | null;
  accessToken?: string;
  initialActiveTeachers?: AdminUserSummary[];
  initialTeacherInvitations?: TeacherInvitationView[];
}

export function AdminDashboardClient({
  adminName,
  overview,
  operationsHealth = null,
  accessToken = "",
  initialActiveTeachers = [],
  initialTeacherInvitations = [],
}: AdminDashboardClientProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <section className="tf-animate-enter rounded-2xl border border-slate-800 bg-gradient-to-br from-[#0b1221] via-[#111b31] to-[#0f172a] p-6 text-white shadow-md sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-teal-300">
              Authorized Admin Studio
            </p>
            <h1 className="mt-1.5 text-3xl font-bold tracking-tight text-white sm:text-[34px]">
              Curriculum &amp; Assessment Control Center — {adminName}
            </h1>
            <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-300">
              All user counts, course oversight metrics, and system health probes
              below are queried live from PostgreSQL with strict Admin RBAC.
            </p>
          </div>
          <div className="flex flex-wrap gap-2.5">
            <Link
              href="/admin/audit"
              className="rounded-xl bg-teal-400 px-4 py-2.5 text-[15px] font-semibold text-slate-950 transition hover:bg-teal-300"
            >
              Manage Users &amp; Roles
            </Link>
            <Link
              href="/admin/problems"
              className="rounded-xl bg-indigo-600 px-4 py-2.5 text-[15px] font-semibold text-white transition hover:bg-indigo-500"
            >
              Open Problem Studio
            </Link>
            <Link
              href="/admin/curriculum"
              className="rounded-xl border border-slate-600 bg-slate-900/70 px-4 py-2.5 text-[15px] font-semibold text-white transition hover:bg-slate-800"
            >
              Manage Lessons &amp; Tracks
            </Link>
          </div>
        </div>

        {/* Real Platform Users & Course Oversight Counters */}
        <div className="mt-6 grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 p-4">
            <div className="flex items-center justify-between text-xs font-semibold uppercase text-slate-400">
              <span>Students</span>
              <GraduationCap className="h-4 w-4 text-teal-300" aria-hidden="true" />
            </div>
            <p className="mt-1.5 text-3xl font-bold text-white">
              {overview.students_count ?? 0}
            </p>
            <p className="mt-1 text-xs text-slate-400">DB-backed student role</p>
          </div>
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 p-4">
            <div className="flex items-center justify-between text-xs font-semibold uppercase text-slate-400">
              <span>Teachers</span>
              <Users className="h-4 w-4 text-indigo-300" aria-hidden="true" />
            </div>
            <p className="mt-1.5 text-3xl font-bold text-white">
              {overview.teachers_count ?? 0}
            </p>
            <p className="mt-1 text-xs text-slate-400">Approved instructors</p>
          </div>
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 p-4">
            <div className="flex items-center justify-between text-xs font-semibold uppercase text-slate-400">
              <span>Admins</span>
              <ShieldCheck className="h-4 w-4 text-amber-300" aria-hidden="true" />
            </div>
            <p className="mt-1.5 text-3xl font-bold text-white">
              {overview.admins_count ?? 0}
            </p>
            <p className="mt-1 text-xs text-slate-400">Authorized governors</p>
          </div>
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 p-4">
            <div className="flex items-center justify-between text-xs font-semibold uppercase text-slate-400">
              <span>Courses &amp; Enrollments</span>
              <BookOpen className="h-4 w-4 text-teal-300" aria-hidden="true" />
            </div>
            <p className="mt-1.5 text-3xl font-bold text-white">
              {overview.courses_active ?? 0}
              <span className="ml-1.5 text-sm font-normal text-slate-400">
                / {overview.courses_total ?? 0} active
              </span>
            </p>
            <p className="mt-1 text-xs text-slate-400">
              {overview.enrollments_active ?? 0} enrollments ·{" "}
              {overview.assignments_published ?? 0} published assignments
            </p>
          </div>
        </div>
      </section>

      {operationsHealth ? (
        <section
          aria-label="Live infrastructure health"
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-indigo-600" />
              <h2 className="text-sm font-bold text-slate-900">
                Live Infrastructure &amp; AI Operations Telemetry
              </h2>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <Badge
                variant={
                  operationsHealth.overall_status === "ok" ? "emerald" : "amber"
                }
              >
                {operationsHealth.overall_status}
              </Badge>
              <Badge
                variant={
                  operationsHealth.llm_provider_mode === "live_llm"
                    ? "emerald"
                    : "amber"
                }
              >
                LLM: {operationsHealth.llm_provider_mode}
              </Badge>
              <Badge variant="neutral">
                Rate Limit:{" "}
                {operationsHealth.rate_limit_enabled ? "enabled" : "off"}
              </Badge>
            </div>
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {operationsHealth.checks.map((chk) => (
              <div
                key={chk.name}
                className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-semibold text-slate-800">
                    {chk.name}
                  </span>
                  <Badge
                    variant={
                      chk.status === "ok"
                        ? "emerald"
                        : chk.status === "degraded"
                          ? "amber"
                          : "rose"
                    }
                  >
                    {chk.status}
                  </Badge>
                </div>
                <p className="mt-1 text-[11px] text-slate-600">{chk.detail}</p>
                {chk.latency_ms != null ? (
                  <p className="mt-0.5 font-mono text-[10px] text-slate-500">
                    {chk.latency_ms} ms
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {/* Primary KPI Grid */}
      <TeacherManagementSection
        accessToken={accessToken}
        initialActiveTeachers={initialActiveTeachers}
        initialInvitations={initialTeacherInvitations}
      />

      <section
        aria-label="Platform content statistics"
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Problem Bank</span>
            <Layers className="h-4 w-4 text-indigo-600" />
          </div>
          <p className="mt-2 text-3xl font-bold text-slate-900">
            {overview.problems_published}
            <span className="ml-1.5 text-sm font-medium text-slate-500">
              / {overview.problems_total} published
            </span>
          </p>
          <p className="mt-1 text-xs text-slate-600">
            {overview.problems_intermediate_or_advanced} Intermediate &amp;
            Advanced · {overview.problems_draft} drafts ·{" "}
            {overview.problems_archived} archived
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Review &amp; Validation Queue</span>
            <ClipboardCheck className="h-4 w-4 text-amber-600" />
          </div>
          <p className="mt-2 text-3xl font-bold text-slate-900">
            {overview.problems_validated +
              overview.problems_in_review +
              overview.problems_approved}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            {overview.problems_validated} validated ·{" "}
            {overview.problems_in_review} in review ·{" "}
            {overview.problems_approved} approved
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Curriculum &amp; Skill Graph</span>
            <BookOpen className="h-4 w-4 text-teal-600" />
          </div>
          <p className="mt-2 text-3xl font-bold text-slate-900">
            {overview.lessons_published}
            <span className="ml-1.5 text-sm font-medium text-slate-500">
              lessons live
            </span>
          </p>
          <p className="mt-1 text-xs text-slate-600">
            {overview.skill_nodes_count} Skill Graph DAG nodes across 4 tracks
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Diagnostics &amp; RAG Corpus</span>
            <Database className="h-4 w-4 text-emerald-600" />
          </div>
          <p className="mt-2 text-3xl font-bold text-slate-900">
            {overview.diagnostic_published}
            <span className="ml-1.5 text-sm font-medium text-slate-500">
              items ({overview.diagnostic_stretch_count} stretch)
            </span>
          </p>
          <p className="mt-1 text-xs text-slate-600">
            {overview.knowledge_approved}/{overview.knowledge_total} RAG docs
            approved for Mentor
          </p>
        </div>
      </section>

      {/* Curriculum Track Coverage */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Learner Track Curriculum Coverage
            </h2>
            <p className="text-xs text-slate-600">
              Live published lesson &amp; problem density across all four tracks.
            </p>
          </div>
          <Link
            href="/admin/curriculum"
            className="text-xs font-semibold text-indigo-700 hover:underline"
          >
            Edit Tracks &amp; Lessons →
          </Link>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {overview.track_coverage.map((track) => (
            <div
              key={track.track_slug}
              className="rounded-xl border border-slate-200 bg-slate-50 p-4"
            >
              <p className="text-xs font-bold text-indigo-800">
                {track.title_en}
              </p>
              <p className="text-[11px] text-slate-500">{track.title_bn}</p>
              <div className="mt-3 flex items-center justify-between text-xs font-semibold text-slate-800">
                <span>{track.lesson_count} lessons</span>
                <span>{track.problem_count} problems</span>
              </div>
              <p className="mt-2 truncate text-[11px] text-slate-500">
                Skills: {track.focus_skills.slice(0, 3).join(", ")}
              </p>
            </div>
          ))}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Review Queue */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-amber-600" />
              <h2 className="text-base font-bold text-slate-900">
                Content Review &amp; Publishing Queue
              </h2>
            </div>
            <Link
              href="/admin/problems"
              className="text-xs font-semibold text-indigo-700 hover:underline"
            >
              View Studio →
            </Link>
          </div>

          {overview.review_queue.length === 0 ? (
            <div className="mt-4 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-900">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
              <span>
                All validated problem versions are already reviewed and
                published.
              </span>
            </div>
          ) : (
            <div className="mt-4 space-y-2">
              {overview.review_queue.map((item) => (
                <Link
                  key={item.version_id}
                  href={`/admin/problems?problem=${item.problem_id}`}
                  className="flex items-center justify-between rounded-xl border border-slate-200 p-3 text-xs transition hover:border-indigo-400 hover:bg-indigo-50/40"
                >
                  <div>
                    <p className="font-semibold text-slate-900">
                      {item.title}{" "}
                      <span className="font-mono text-[11px] text-slate-500">
                        (v{item.version_number})
                      </span>
                    </p>
                    <p className="text-[11px] text-slate-500">
                      {item.slug} · {item.difficulty} · {item.mode}
                    </p>
                  </div>
                  <Badge variant="amber">{item.status}</Badge>
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* Recent Immutable Audit Logs */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-indigo-600" />
              <h2 className="text-base font-bold text-slate-900">
                Recent Admin &amp; Governance Audit Trail
              </h2>
            </div>
            <Link
              href="/admin/audit"
              className="text-xs font-semibold text-indigo-700 hover:underline"
            >
              Full Audit &amp; Roles →
            </Link>
          </div>

          <div className="mt-4 space-y-2">
            {overview.recent_audit_logs.slice(0, 7).map((log) => (
              <div
                key={log.id}
                className="flex items-start justify-between gap-2 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2 text-xs"
              >
                <div className="min-w-0">
                  <p className="font-mono font-semibold text-slate-900">
                    {log.action}
                  </p>
                  <p className="truncate text-[11px] text-slate-600">
                    {log.target_type} ·{" "}
                    {log.actor_email || log.actor_user_id || "system"}
                  </p>
                </div>
                <span className="shrink-0 text-[10px] text-slate-500">
                  {new Date(log.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
