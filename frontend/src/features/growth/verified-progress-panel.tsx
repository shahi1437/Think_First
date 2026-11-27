"use client";

import {
  Activity,
  Award,
  CheckCircle2,
  ClipboardCheck,
  Code2,
  Compass,
  Info,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { getLanguageDisplayName } from "@/lib/languages";
import type { VerifiedLearningProgressView } from "@/types/growth";

interface VerifiedProgressPanelProps {
  progress: VerifiedLearningProgressView;
  language?: "en" | "bn";
}

const TREND_META: Record<
  VerifiedLearningProgressView["improvement_trend"],
  { labelEn: string; labelBn: string; badgeClass: string }
> = {
  improving: {
    labelEn: "Improving",
    labelBn: "উন্নতি হচ্ছে",
    badgeClass: "border-emerald-200 bg-emerald-50 text-emerald-800",
  },
  steady: {
    labelEn: "Steady",
    labelBn: "স্থিতিশীল",
    badgeClass: "border-teal-200 bg-teal-50 text-teal-800",
  },
  needs_focus: {
    labelEn: "Needs Focus",
    labelBn: "অতিরিক্ত মনোযোগ প্রয়োজন",
    badgeClass: "border-amber-200 bg-amber-50 text-amber-800",
  },
  insufficient_data: {
    labelEn: "Collecting Baseline (<4 runs)",
    labelBn: "তথ্য সংগ্রহ চলছে (<৪টি রান)",
    badgeClass: "border-slate-200 bg-slate-100 text-slate-700",
  },
};

export function VerifiedProgressPanel({
  progress,
  language = "en",
}: VerifiedProgressPanelProps) {
  const isBn = language === "bn";
  const trend = TREND_META[progress.improvement_trend];
  const maxDailyActivity = Math.max(
    1,
    ...progress.daily_activity_14d.map(
      (d) => d.submissions_count + d.lessons_completed,
    ),
  );
  const acceptanceRate =
    progress.total_submissions > 0
      ? Math.round(
          (progress.accepted_submissions / progress.total_submissions) * 100,
        )
      : null;

  return (
    <section
      aria-label="Verified learning progress"
      data-testid="verified-progress-panel"
      className="rounded-2xl border border-slate-200 bg-white p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck
              className="h-4 w-4 text-teal-700"
              aria-hidden="true"
            />
            <p className="text-xs font-semibold text-teal-700">
              {isBn
                ? "প্রমাণভিত্তিক অগ্রগতি"
                : "Execution-Verified Learning Progress"}
            </p>
          </div>
          <h2 className="mt-1 text-lg font-bold tracking-tight text-slate-950">
            {isBn
              ? "যাচাইকৃত অর্জন বনাম চলমান অনুশীলন"
              : "Verified Achievements vs. Estimated In-Progress"}
          </h2>
          <p className="mt-1 text-xs text-slate-600">
            {progress.methodology_note}
          </p>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium ${trend.badgeClass}`}
        >
          <TrendingUp className="h-3.5 w-3.5" aria-hidden="true" />
          <span>{isBn ? trend.labelBn : trend.labelEn}</span>
        </span>
      </div>

      {/* Primary Split: Verified Achievements (left 8 cols) vs Estimated / In-Progress (right 4 cols) */}
      <div className="mt-5 grid gap-5 lg:grid-cols-12">
        {/* Verified Column */}
        <div
          data-testid="verified-achievements-group"
          className="space-y-4 lg:col-span-8"
        >
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-800">
              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
              {isBn
                ? "যাচাইকৃত অর্জন (স্যান্ডবক্স ও প্রকাশিত গ্রেড)"
                : "Verified Achievements (Sandbox & Published Grades)"}
            </span>
            {acceptanceRate !== null ? (
              <span className="text-xs text-slate-500 tabular-nums">
                {progress.accepted_submissions}/{progress.total_submissions}{" "}
                accepted ({acceptanceRate}%)
              </span>
            ) : null}
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-emerald-200/80 bg-emerald-50/40 p-3.5">
              <p className="text-xs font-medium text-slate-600">
                Problems Solved
              </p>
              <p className="mt-1 text-2xl font-bold text-slate-950 tabular-nums">
                {progress.problems_solved_verified}
                <span className="ml-1 text-xs font-normal text-slate-500">
                  / {progress.problems_attempted} tried
                </span>
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5">
              <p className="text-xs font-medium text-slate-600">
                Assignments Done
              </p>
              <p className="mt-1 text-2xl font-bold text-slate-950 tabular-nums">
                {progress.assignments_completed_verified}
                <span className="ml-1 text-xs font-normal text-slate-500">
                  / {progress.assignments_total}
                </span>
              </p>
              <p className="mt-0.5 text-[11px] text-slate-500 tabular-nums">
                {progress.average_published_grade_pct !== null
                  ? `Avg grade: ${progress.average_published_grade_pct}%`
                  : "No published grades yet"}
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5">
              <p className="text-xs font-medium text-slate-600">
                Transfer &amp; Retention
              </p>
              <p className="mt-1 text-2xl font-bold text-slate-950 tabular-nums">
                {progress.transfer_verifications_passed +
                  progress.retention_checks_passed}
              </p>
              <p className="mt-0.5 text-[11px] text-slate-500 tabular-nums">
                {progress.transfer_verifications_passed} transfer ·{" "}
                {progress.retention_checks_passed} retained
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5">
              <p className="text-xs font-medium text-slate-600">
                14-Day Consistency
              </p>
              <p className="mt-1 text-2xl font-bold text-slate-950 tabular-nums">
                {progress.consistency_active_days_14d}
                <span className="ml-1 text-xs font-normal text-slate-500">
                  / 14 days
                </span>
              </p>
              {progress.early_acceptance_rate_pct !== null &&
              progress.recent_acceptance_rate_pct !== null ? (
                <p className="mt-0.5 text-[11px] text-slate-500 tabular-nums">
                  Pass rate: {progress.early_acceptance_rate_pct}% →{" "}
                  {progress.recent_acceptance_rate_pct}%
                </p>
              ) : (
                <p className="mt-0.5 text-[11px] text-slate-500">
                  Factual daily log
                </p>
              )}
            </div>
          </div>

          {/* 14-day factual activity bars + Language breakdown */}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-slate-200 p-4">
              <div className="flex items-center justify-between text-xs">
                <span className="inline-flex items-center gap-1.5 font-semibold text-slate-800">
                  <Activity
                    className="h-3.5 w-3.5 text-teal-700"
                    aria-hidden="true"
                  />
                  Last 14 Days Activity
                </span>
                <span className="text-[11px] text-slate-500 tabular-nums">
                  {progress.consistency_active_days_14d} active day(s)
                </span>
              </div>
              <div
                className="mt-3 flex h-16 items-end gap-1"
                aria-label="14-day activity chart"
              >
                {progress.daily_activity_14d.map((pt) => {
                  const total = pt.submissions_count + pt.lessons_completed;
                  const heightPct =
                    total === 0
                      ? 8
                      : Math.max(18, Math.round((total / maxDailyActivity) * 100));
                  return (
                    <div
                      key={pt.day}
                      title={`${pt.day}: ${pt.submissions_count} run(s), ${pt.accepted_count} accepted, ${pt.lessons_completed} lesson(s)`}
                      className="flex flex-1 flex-col items-center justify-end"
                    >
                      <div
                        className={`w-full rounded-sm transition-all ${
                          pt.accepted_count > 0
                            ? "bg-teal-600"
                            : total > 0
                              ? "bg-slate-400"
                              : "bg-slate-200"
                        }`}
                        style={{ height: `${heightPct}%` }}
                      />
                    </div>
                  );
                })}
              </div>
              <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
                <span>14 days ago</span>
                <span>Today</span>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 p-4">
              <div className="flex items-center justify-between text-xs">
                <span className="inline-flex items-center gap-1.5 font-semibold text-slate-800">
                  <Code2
                    className="h-3.5 w-3.5 text-teal-700"
                    aria-hidden="true"
                  />
                  Languages Practiced
                </span>
                <span className="text-[11px] text-slate-500 tabular-nums">
                  {progress.languages_used.length} language(s)
                </span>
              </div>
              {progress.languages_used.length === 0 ? (
                <p className="mt-3 text-xs text-slate-500">
                  Submit a coding solution or complete a lesson exercise to
                  record per-language mastery.
                </p>
              ) : (
                <div className="mt-2.5 space-y-1.5">
                  {progress.languages_used.map((lg) => (
                    <div
                      key={lg.language_slug}
                      className="flex items-center justify-between rounded-lg bg-slate-50 px-2.5 py-1.5 text-xs"
                    >
                      <span className="font-medium text-slate-800">
                        {getLanguageDisplayName(lg.language_slug)}
                      </span>
                      <span className="font-mono text-[11px] text-slate-600 tabular-nums">
                        {lg.problems_solved_verified}/{lg.problems_attempted}{" "}
                        solved · {lg.lessons_completed} lessons
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Mastered Verified Concepts */}
          <div>
            <p className="text-xs font-semibold text-slate-700">
              Verified Mastered Concepts ({progress.concepts_mastered_verified.length})
            </p>
            {progress.concepts_mastered_verified.length === 0 ? (
              <p className="mt-1 text-xs text-slate-500">
                Pass independent coding problems or transfer checks without
                hints to verify concepts here.
              </p>
            ) : (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {progress.concepts_mastered_verified.map((slug) => (
                  <span
                    key={slug}
                    className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-mono text-xs text-emerald-900"
                  >
                    <Award className="h-3 w-3" aria-hidden="true" />
                    {slug}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Estimated / In-Progress Column */}
        <aside
          data-testid="estimated-progress-group"
          className="flex flex-col justify-between rounded-xl border border-slate-200 bg-[#f7f8fa] p-4 lg:col-span-4"
        >
          <div className="space-y-4">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
              <Compass className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
              {isBn
                ? "অনুমিত ও চলমান (এখনো যাচাই হয়নি)"
                : "Estimated & In-Progress"}
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2.5">
                <span className="text-slate-600">Guided Lessons Done</span>
                <span className="font-semibold text-slate-950 tabular-nums">
                  {progress.estimated_lessons_completed}
                </span>
              </div>
              <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2.5">
                <span className="text-slate-600">Diagnostics Completed</span>
                <span className="font-semibold text-slate-950 tabular-nums">
                  {progress.estimated_diagnostic_sessions}
                </span>
              </div>
              <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2.5">
                <span className="text-slate-600">Guided / Emerging Skills</span>
                <span className="font-semibold text-slate-950 tabular-nums">
                  {progress.estimated_guided_skills_count}
                </span>
              </div>
            </div>

            <div>
              <p className="text-xs font-medium text-slate-700">
                Concepts Currently In Progress ({progress.concepts_in_progress.length})
              </p>
              {progress.concepts_in_progress.length === 0 ? (
                <p className="mt-1 text-xs text-slate-500">
                  No unverified guided concepts right now.
                </p>
              ) : (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {progress.concepts_in_progress.map((slug) => (
                    <span
                      key={slug}
                      className="rounded-md border border-slate-200 bg-white px-2 py-0.5 font-mono text-[11px] text-slate-700"
                    >
                      {slug}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="mt-4 flex items-start gap-2 rounded-lg border border-slate-200 bg-white p-3 text-[11px] leading-relaxed text-slate-600">
            <Info
              className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400"
              aria-hidden="true"
            />
            <span>
              <ClipboardCheck className="mr-1 inline h-3 w-3 text-teal-700" />
              Guided lessons and diagnostic estimates help plan next steps, but
              never count as verified mastery until proven in isolated code
              execution.
            </span>
          </div>
        </aside>
      </div>
    </section>
  );
}
