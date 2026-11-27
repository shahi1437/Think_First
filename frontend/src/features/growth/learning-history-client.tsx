"use client";

import {
  AlertCircle,
  ArrowUpRight,
  Clock,
  History,
  Loader2,
  Search,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { DebuggingTimelinePanel } from "@/features/growth/debugging-timeline-panel";
import { fetchLearningHistory } from "@/lib/api-client";
import type {
  DebuggingTimelineResponseView,
  HistoryCategory,
  LearningHistoryResponseView,
} from "@/types/growth";

interface LearningHistoryClientProps {
  accessToken: string;
  initialHistory: LearningHistoryResponseView;
  initialDebuggingTimeline?: DebuggingTimelineResponseView | null;
  initialLanguage?: "en" | "bn";
}

const CATEGORIES: Array<{
  value: HistoryCategory | "";
  labelEn: string;
  labelBn: string;
}> = [
  { value: "", labelEn: "All Events", labelBn: "সব ইভেন্ট" },
  { value: "lesson", labelEn: "Lessons", labelBn: "লেসন" },
  { value: "diagnostic", labelEn: "Diagnostics", labelBn: "ডায়াগনস্টিক" },
  { value: "submission", labelEn: "Judge0", labelBn: "Judge0" },
  { value: "revision", labelEn: "Revisions", labelBn: "রিভিশন" },
  { value: "mentor", labelEn: "AI Mentor", labelBn: "AI মেন্টর" },
  { value: "hint", labelEn: "Hints", labelBn: "হিন্ট" },
  { value: "transfer", labelEn: "Transfer", labelBn: "ট্রান্সফার" },
  { value: "skill", labelEn: "Skill Graph", labelBn: "স্কিল গ্রাফ" },
  { value: "daily_plan", labelEn: "Daily Plan", labelBn: "দৈনিক প্ল্যান" },
  { value: "retention", labelEn: "Retention", labelBn: "রিটেনশন" },
];

const CATEGORY_VARIANT: Record<
  string,
  "teal" | "indigo" | "amber" | "neutral"
> = {
  lesson: "indigo",
  diagnostic: "indigo",
  submission: "teal",
  revision: "neutral",
  mentor: "indigo",
  hint: "amber",
  transfer: "teal",
  skill: "teal",
  daily_plan: "neutral",
  retention: "teal",
};

export function LearningHistoryClient({
  accessToken,
  initialHistory,
  initialDebuggingTimeline = null,
  initialLanguage = "en",
}: LearningHistoryClientProps) {
  const [lang, setLang] = useState<"en" | "bn">(initialLanguage);
  const [history, setHistory] =
    useState<LearningHistoryResponseView>(initialHistory);
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<
    HistoryCategory | ""
  >("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isBn = lang === "bn";

  async function runFilter(nextQ: string, nextCat: HistoryCategory | "") {
    setError(null);
    setLoading(true);
    try {
      const updated = await fetchLearningHistory(accessToken, {
        q: nextQ,
        category: nextCat,
        limit: 50,
      });
      setHistory(updated);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not search learning history.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6" lang={lang}>
      <section className="tf-animate-enter rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-700">
              <History className="h-3.5 w-3.5" aria-hidden="true" />
              <span>
                {isBn ? "দীর্ঘমেয়াদী শেখার ইতিহাস" : "Persistent Learning History"}
              </span>
            </p>
            <h1 className="mt-1.5 text-3xl font-bold tracking-tight text-slate-900">
              {isBn ? "তোমার সম্পূর্ণ টাইমলাইন" : "Your Complete Learning Timeline"}
            </h1>
            <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-slate-600">
              {isBn
                ? "লেসন, ডায়াগনস্টিক, স্যান্ডবক্স ফলাফল, কোড রিভিশন, AI মেন্টর, হিন্ট, ট্রান্সফার, স্কিল পরিবর্তন ও রিটেনশন ইভেন্ট খুঁজুন।"
                : "Search and filter every persisted lesson, diagnostic, sandbox verdict, code revision, AI Mentor turn, hint, transfer check, skill change, and retention verification."}
            </p>
          </div>

          <div
            role="group"
            aria-label="History language"
            className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-xs"
          >
            <button
              type="button"
              onClick={() => setLang("en")}
              aria-pressed={lang === "en"}
              className={`rounded-md px-2.5 py-1 font-semibold ${
                lang === "en"
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
              className={`rounded-md px-2.5 py-1 font-semibold ${
                lang === "bn"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-600 hover:bg-slate-200/70"
              }`}
            >
              বাংলা
            </button>
          </div>
        </div>

        {/* Search Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void runFilter(query, selectedCategory);
          }}
          className="mt-5 flex flex-wrap gap-2"
        >
          <div className="relative min-w-0 flex-1">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
              aria-hidden="true"
            />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label={isBn ? "ইতিহাস অনুসন্ধান" : "Search learning history"}
              placeholder={
                isBn
                  ? "দক্ষতা, লেসন, Judge0 বা ফলাফল দিয়ে খুঁজুন..."
                  : "Search by skill, lesson, verdict, mentor turn, or retention..."
              }
              className="w-full rounded-xl border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-60"
          >
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            ) : (
              <Search className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            <span>{isBn ? "খুঁজুন" : "Search"}</span>
          </button>
        </form>

        {/* Category Filter Chips */}
        <div
          role="group"
          aria-label="Filter timeline by category"
          className="mt-3 flex flex-wrap gap-1.5"
        >
          {CATEGORIES.map((cat) => {
            const count =
              cat.value === ""
                ? Object.values(history.category_counts).reduce(
                    (acc, n) => acc + n,
                    0,
                  )
                : (history.category_counts[cat.value] ?? 0);
            const active = selectedCategory === cat.value;
            return (
              <button
                key={cat.value || "all"}
                type="button"
                aria-pressed={active}
                onClick={() => {
                  setSelectedCategory(cat.value);
                  void runFilter(query, cat.value);
                }}
                className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                  active
                    ? "bg-slate-900 text-white"
                    : "border border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100"
                }`}
              >
                {isBn ? cat.labelBn : cat.labelEn} ({count})
              </button>
            );
          })}
        </div>

        {error ? (
          <div
            role="alert"
            className="mt-4 flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800"
          >
            <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </div>
        ) : null}
      </section>

      {/* Phase 11 Feature 1: Per-Problem AI Debugging Timeline */}
      {initialDebuggingTimeline ? (
        <DebuggingTimelinePanel
          timeline={initialDebuggingTimeline}
          language={lang}
        />
      ) : null}

      {/* Timeline Feed */}
      <section aria-label="Learning timeline events" className="space-y-3">
        {history.items.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-600">
            {isBn
              ? "এই ফিল্টারে এখনো কোনো ইভেন্ট পাওয়া যায়নি।"
              : "No learning events match this filter yet. Complete a lesson, diagnostic, or Judge0 submission to populate your timeline."}
          </div>
        ) : (
          history.items.map((item) => (
            <article
              key={item.id}
              className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={CATEGORY_VARIANT[item.category] ?? "neutral"}>
                      {item.category.replace("_", " ")}
                    </Badge>
                    {item.verdict_or_status ? (
                      <Badge variant="neutral">{item.verdict_or_status}</Badge>
                    ) : null}
                    {item.skill_slug ? (
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-600">
                        {item.skill_slug}
                      </span>
                    ) : null}
                  </div>
                  <h2 className="mt-1.5 text-sm font-bold text-slate-900">
                    {isBn ? item.title_bn : item.title_en}
                  </h2>
                  <p className="mt-1 text-xs leading-relaxed text-slate-600">
                    {isBn ? item.summary_bn : item.summary_en}
                  </p>
                </div>

                <div className="flex flex-col items-end gap-1.5 text-[11px] text-slate-500">
                  <span className="inline-flex items-center gap-1">
                    <Clock className="h-3 w-3" aria-hidden="true" />
                    {new Date(item.occurred_at).toLocaleString()}
                  </span>
                  {item.href ? (
                    <Link
                      href={item.href}
                      className="inline-flex items-center gap-1 font-semibold text-indigo-700 hover:underline"
                    >
                      <span>{isBn ? "খুলুন" : "View"}</span>
                      <ArrowUpRight className="h-3 w-3" aria-hidden="true" />
                    </Link>
                  ) : null}
                </div>
              </div>
            </article>
          ))
        )}
      </section>
    </div>
  );
}
