"use client";

import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  Play,
  ShieldCheck,
  Timer,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  fetchRetentionOverview,
  submitRetentionAttempt,
} from "@/lib/api-client";
import { getLanguageDisplayName } from "@/lib/languages";
import type {
  RetentionAttemptView,
  RetentionOverviewView,
  RetentionScheduleView,
} from "@/types/growth";

interface RetentionClientProps {
  accessToken: string;
  initialOverview: RetentionOverviewView;
  initialLanguage?: "en" | "bn";
  activeLanguageSlug?: string;
}

const STATUS_BADGE: Record<
  string,
  { label: string; variant: "teal" | "indigo" | "amber" | "neutral" }
> = {
  due: { label: "Due Now (>=24h)", variant: "teal" },
  scheduled: { label: "Scheduled (Waiting 24h)", variant: "indigo" },
  passed_retained: { label: "Retained Verified", variant: "teal" },
  needs_review: { label: "Needs Review", variant: "amber" },
};

export function RetentionClient({
  accessToken,
  initialOverview,
  initialLanguage = "en",
  activeLanguageSlug = "python",
}: RetentionClientProps) {
  const [lang, setLang] = useState<"en" | "bn">(initialLanguage);
  const [overview, setOverview] =
    useState<RetentionOverviewView>(initialOverview);
  const [activeScheduleId, setActiveScheduleId] = useState<string | null>(
    initialOverview.schedules[0]?.id ?? null,
  );
  const [codeBySchedule, setCodeBySchedule] = useState<Record<string, string>>(
    () =>
      Object.fromEntries(
        initialOverview.schedules.map((s) => [s.id, s.starter_code]),
      ),
  );
  const [explanation, setExplanation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [lastResult, setLastResult] = useState<RetentionAttemptView | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const isBn = lang === "bn";

  const activeSchedule: RetentionScheduleView | null =
    overview.schedules.find((s) => s.id === activeScheduleId) ??
    overview.schedules[0] ??
    null;
  const activeScheduleLanguageSlug =
    activeSchedule?.language_slug ?? activeLanguageSlug ?? "python";
  const activeScheduleLanguageLabel = getLanguageDisplayName(
    activeScheduleLanguageSlug,
  );

  async function handleSubmitRetention(e: React.FormEvent) {
    e.preventDefault();
    if (!activeSchedule) return;
    setError(null);
    setSubmitting(true);
    try {
      const code =
        codeBySchedule[activeSchedule.id] ?? activeSchedule.starter_code;
      const attempt = await submitRetentionAttempt(
        accessToken,
        activeSchedule.id,
        {
          language_slug: activeScheduleLanguageSlug,
          source_code: code,
          student_explanation: explanation.trim(),
        },
      );
      setLastResult(attempt);
      setExplanation("");
      const refreshed = await fetchRetentionOverview(accessToken);
      setOverview(refreshed);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not evaluate retention submission.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6" lang={lang}>
      <section className="tf-animate-enter rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-teal-700">
              <Timer className="h-3.5 w-3.5" aria-hidden="true" />
              <span>
                {isBn ? "দীর্ঘমেয়াদী রিটেনশন যাচাই" : "Spaced Retention Verification"}
              </span>
            </p>
            <h1 className="mt-1.5 text-3xl font-bold tracking-tight text-slate-900">
              {isBn
                ? "আসল Judge0 দিয়ে দীর্ঘমেয়াদী দক্ষতা প্রমাণ করো"
                : "Prove Long-Term Retention with Delayed Judge0 Checks"}
            </h1>
            <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-slate-600">
              {isBn ? overview.policy_note_bn : overview.policy_note_en}
            </p>
          </div>

          <div
            role="group"
            aria-label="Retention language"
            className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-xs"
          >
            <button
              type="button"
              onClick={() => setLang("en")}
              aria-pressed={lang === "en"}
              className={`rounded-md px-2.5 py-1 font-semibold ${lang === "en"
                ? "bg-indigo-600 text-white"
                : "text-slate-600 hover:bg-slate-200/70"
                }`}
            >
              English
            </button>
            <button
              type="button"
              onClick={() => setLang("bn")}
              aria-pressed={lang === "bn"}
              className={`rounded-md px-2.5 py-1 font-semibold ${lang === "bn"
                ? "bg-indigo-600 text-white"
                : "text-slate-600 hover:bg-slate-200/70"
                }`}
            >
              বাংলা
            </button>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
            <p className="text-[11px] font-semibold uppercase text-slate-500">
              {isBn ? "মোট সূচি" : "Tracked Schedules"}
            </p>
            <p className="mt-1 text-lg font-bold text-slate-900">
              {overview.schedules.length}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
            <p className="text-[11px] font-semibold uppercase text-slate-500">
              {isBn ? "এখন বাকি (২৪ ঘণ্টা পূর্ণ)" : "Due Now (>=24h)"}
            </p>
            <p className="mt-1 text-lg font-bold text-teal-700">
              {overview.due_count}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
            <p className="text-[11px] font-semibold uppercase text-slate-500">
              {isBn ? "Retained দক্ষতা" : "Retained Skills"}
            </p>
            <p className="mt-1 text-lg font-bold text-indigo-700">
              {overview.retained_skills_count}
            </p>
          </div>
        </div>
      </section>

      {overview.schedules.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
          <p className="text-sm font-semibold text-slate-800">
            {isBn
              ? "এখনো কোনো রিটেনশন সূচি তৈরি হয়নি।"
              : "No retention checks scheduled yet."}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            {isBn
              ? "একটি লেসন অনুশীলন, কোডিং সমস্যা বা ট্রান্সফার চ্যালেঞ্জ পাস করলে স্বয়ংক্রিয়ভাবে ২৪ ঘণ্টা পরের রিটেনশন সূচি তৈরি হবে।"
              : "Complete a guided lesson Judge0 exercise, Problem Bank solve, or Transfer Challenge first — a 24-hour spaced retention check will be scheduled automatically."}
          </p>
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            <Link
              href="/student/lessons"
              className="rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-indigo-500"
            >
              {isBn ? "লেসন শুরু করো" : "Open Beginner Lessons"}
            </Link>
            <Link
              href="/student/problems"
              className="rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              {isBn ? "প্রবলেম ব্যাংক" : "Open Problem Bank"}
            </Link>
          </div>
        </section>
      ) : (
        <section className="grid gap-6 lg:grid-cols-12">
          {/* Left: Retention Schedule List */}
          <div className="space-y-3 lg:col-span-5">
            <h2 className="text-sm font-bold text-slate-900">
              {isBn ? "নির্ধারিত রিটেনশন চেকসমূহ" : "Scheduled Retention Checks"}
            </h2>
            {overview.schedules.map((sched) => {
              const badge = STATUS_BADGE[sched.status] ?? {
                label: sched.status,
                variant: "neutral" as const,
              };
              const selected = activeSchedule?.id === sched.id;
              return (
                <button
                  key={sched.id}
                  type="button"
                  onClick={() => setActiveScheduleId(sched.id)}
                  className={`w-full rounded-2xl border p-4 text-left transition ${selected
                    ? "border-indigo-600 bg-indigo-50/40 ring-1 ring-indigo-600"
                    : "border-slate-200 bg-white hover:border-indigo-300"
                    }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-sm font-bold text-slate-900">
                      {isBn ? sched.skill_title_bn : sched.skill_title_en}
                    </span>
                    <Badge variant={badge.variant}>{badge.label}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-slate-600">
                    {sched.problem_title}
                  </p>
                  <p className="mt-1.5 inline-flex items-center gap-1 text-[11px] text-slate-500">
                    <Clock className="h-3 w-3" aria-hidden="true" />
                    {sched.is_due_now
                      ? isBn
                        ? "২৪ ঘণ্টা পূর্ণ — এখনই যাচাই করা যাবে"
                        : "Eligible now for Retained verification"
                      : isBn
                        ? `Retained উন্মুক্ত হতে বাকি: ~${sched.hours_until_eligible.toFixed(1)} ঘণ্টা`
                        : `Unlocks Retained in ~${sched.hours_until_eligible.toFixed(1)}h`}
                  </p>
                </button>
              );
            })}
          </div>

          {/* Right: Live Judge0 Retention Check Workspace */}
          {activeSchedule ? (
            <form
              onSubmit={(e) => void handleSubmitRetention(e)}
              className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-7"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h2 className="text-base font-bold text-slate-900">
                    {activeSchedule.problem_title}
                  </h2>
                  <p className="text-xs text-slate-500">
                    Skill:{" "}
                    <span className="font-mono font-semibold text-slate-700">
                      {activeSchedule.skill_slug}
                    </span>{" "}
                    · Source: {activeSchedule.source_evidence_type}
                  </p>
                </div>
                <Link
                  href={`/student/problems/${activeSchedule.problem_id}`}
                  className="text-xs font-semibold text-indigo-700 hover:underline"
                >
                  {isBn ? "সম্পূর্ণ বিবরণ দেখো" : "View full problem"}
                </Link>
              </div>

              {!activeSchedule.is_due_now &&
                activeSchedule.status !== "passed_retained" ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-xs text-amber-900">
                  {isBn
                    ? `এখন অনুশীলন করলে Judge0 ফলাফল সংরক্ষিত হবে, কিন্তু ২৪ ঘণ্টা পূর্ণ না হওয়া পর্যন্ত (~${activeSchedule.hours_until_eligible.toFixed(1)} ঘণ্টা বাকি) Skill Graph-এ Retained হিসেবে চিহ্নিত হবে না।`
                    : `You can practice now on Judge0, but Retention requires >=24h spacing (~${activeSchedule.hours_until_eligible.toFixed(1)}h remaining) before Skill Graph promotes this skill to Retained.`}
                </div>
              ) : null}

              <div>
                <label
                  htmlFor="retention-code"
                  className="block text-sm font-semibold text-slate-800"
                >
                  {isBn
                    ? `${activeScheduleLanguageLabel} সমাধান (স্যান্ডবক্সে যাচাই হবে)`
                    : `${activeScheduleLanguageLabel} Solution (Evaluated in Real Sandbox)`}
                </label>
                <textarea
                  id="retention-code"
                  rows={10}
                  value={
                    codeBySchedule[activeSchedule.id] ??
                    activeSchedule.starter_code
                  }
                  onChange={(e) =>
                    setCodeBySchedule((prev) => ({
                      ...prev,
                      [activeSchedule.id]: e.target.value,
                    }))
                  }
                  className="mt-1.5 w-full rounded-xl border border-slate-300 bg-slate-950 p-3.5 font-mono text-[13px] leading-relaxed text-slate-100 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label
                  htmlFor="retention-explanation"
                  className="block text-sm font-semibold text-slate-800"
                >
                  {isBn
                    ? "তোমার সমাধানের যুক্তি (কমপক্ষে ১০ অক্ষর)"
                    : "Brief Independent Explanation (min 10 characters)"}
                </label>
                <textarea
                  id="retention-explanation"
                  rows={2}
                  required
                  minLength={10}
                  value={explanation}
                  onChange={(e) => setExplanation(e.target.value)}
                  placeholder={
                    isBn
                      ? "কেন তোমার কোড সব টেস্ট ও সীমানা মান পাস করবে তা ব্যাখ্যা করো..."
                      : "Explain why your code handles edge cases correctly without hints..."
                  }
                  className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white p-3 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              {error ? (
                <div
                  role="alert"
                  className="flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800"
                >
                  <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span>{error}</span>
                </div>
              ) : null}

              {lastResult ? (
                <div
                  className={`tf-celebrate-pop rounded-xl border px-4 py-3 text-sm ${lastResult.outcome === "retained_verified"
                    ? "border-teal-200 bg-teal-50 text-teal-900"
                    : "border-amber-200 bg-amber-50 text-amber-900"
                    }`}
                >
                  <p className="flex items-center gap-1.5 font-bold">
                    {lastResult.outcome === "retained_verified" ? (
                      <ShieldCheck className="h-4 w-4 text-teal-700" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4 text-amber-700" />
                    )}
                    <span>
                      Outcome: {lastResult.outcome} ({lastResult.passed_tests}/
                      {lastResult.total_tests} sandbox tests)
                    </span>
                  </p>
                  <p className="mt-1">{lastResult.summary_message}</p>
                </div>
              ) : null}

              <button
                type="submit"
                disabled={submitting || explanation.trim().length < 10}
                className="tf-btn-press inline-flex items-center gap-2 rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-teal-500 disabled:opacity-60"
              >
                {submitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Play className="h-4 w-4" aria-hidden="true" />
                )}
                <span>
                  {isBn
                    ? "Judge0-তে রিটেনশন যাচাই জমা দাও"
                    : "Submit Retention Check to Judge0"}
                </span>
              </button>
            </form>
          ) : null}
        </section>
      )}

      {/* Recent Retention Attempts */}
      {overview.recent_attempts.length > 0 ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-bold text-slate-900">
            {isBn ? "সাম্প্রতিক রিটেনশন প্রচেষ্টা" : "Recent Retention Verification Attempts"}
          </h2>
          <div className="mt-3 space-y-2">
            {overview.recent_attempts.map((att) => (
              <div
                key={att.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      variant={
                        att.outcome === "retained_verified"
                          ? "teal"
                          : att.outcome === "passed_too_early"
                            ? "indigo"
                            : "amber"
                      }
                    >
                      {att.outcome}
                    </Badge>
                    <span className="font-mono font-semibold text-slate-700">
                      {att.skill_slug}
                    </span>
                    <span className="text-slate-600">
                      {att.passed_tests}/{att.total_tests} tests ·{" "}
                      {att.elapsed_hours_since_initial.toFixed(1)}h elapsed
                    </span>
                  </div>
                  <p className="mt-1 text-slate-600">{att.summary_message}</p>
                </div>
                <span className="text-[11px] text-slate-500">
                  {new Date(att.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
