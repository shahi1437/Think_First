"use client";

import {
  ArrowRight,
  BookOpen,
  Calendar,
  CheckCircle2,
  ClipboardCheck,
  Compass,
  Dna,
  History,
  Loader2,
  Sparkles,
  Timer,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { LanguageSelector } from "@/components/language-selector";
import { Badge } from "@/components/ui/badge";
import { SkillGraphPanel } from "@/features/learning/skill-graph-panel";
import { selectLearningTrack } from "@/lib/api-client";
import { getLanguageDisplayName } from "@/lib/languages";
import type {
  LanguageProgressOverview,
  LearningDashboardView,
  StudentTrackStatus,
  TrackSlug,
} from "@/types/learning";

interface LearningDashboardClientProps {
  accessToken: string;
  studentName: string;
  initialDashboard: LearningDashboardView;
  languageOverview?: LanguageProgressOverview;
  initialLanguage?: "en" | "bn";
  dnaSummary?: {
    verifiedCount: number;
    totalDimensions: number;
    strengths: string[];
  };
  dailyPlanSummary?: {
    completedTasks: number;
    totalTasks: number;
    availableMinutes: number;
    versionNumber: number;
  };
  retentionSummary?: {
    dueCount: number;
    scheduledCount: number;
    retainedSkillsCount: number;
  };
  classroomSummary?: {
    enrolledCount: number;
    pendingAssignmentsCount: number;
    totalAssignmentsCount: number;
    recentClasses: Array<{
      courseId: string;
      code: string;
      title: string;
      status: string;
    }>;
  };
}

export function LearningDashboardClient({
  accessToken,
  studentName,
  initialDashboard,
  languageOverview,
  initialLanguage = "en",
  dnaSummary,
  dailyPlanSummary,
  retentionSummary,
  classroomSummary,
}: LearningDashboardClientProps) {
  const [lang, setLang] = useState<"en" | "bn">(initialLanguage);
  const [trackStatus, setTrackStatus] = useState<StudentTrackStatus>(
    initialDashboard.track_status,
  );
  const [savingTrack, setSavingTrack] = useState<TrackSlug | null>(null);
  const [trackError, setTrackError] = useState<string | null>(null);

  const isBn = lang === "bn";
  const activeLanguageLabel = getLanguageDisplayName(
    initialDashboard.language_slug,
  );
  const observedSkills = initialDashboard.skill_graph.nodes.filter(
    (n) => n.state !== "unobserved",
  ).length;
  const verifiedSkills = initialDashboard.skill_graph.nodes.filter((n) =>
    ["independent", "transferred", "retained"].includes(n.state),
  ).length;

  async function handleSelectTrack(slug: TrackSlug) {
    setTrackError(null);
    setSavingTrack(slug);
    try {
      const updated = await selectLearningTrack(accessToken, slug);
      setTrackStatus(updated);
    } catch (err) {
      setTrackError(
        err instanceof Error ? err.message : "Could not update track.",
      );
    } finally {
      setSavingTrack(null);
    }
  }

  return (
    <div className="space-y-6" lang={lang}>
      {/* Hero & Language Switcher */}
      <section className="rounded-2xl border border-slate-800 bg-gradient-to-br from-[#0b1221] via-[#111b31] to-[#0f172a] p-6 text-white shadow-md sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-teal-300">
              {isBn ? "অ্যাডাপ্টিভ লার্নিং ড্যাশবোর্ড" : "Student Learning Workspace"}
            </p>
            <h1 className="mt-1.5 text-3xl font-bold tracking-tight text-white sm:text-[34px]">
              {isBn ? `স্বাগতম, ${studentName}` : `Welcome back, ${studentName}`}
            </h1>
            <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-300">
              {isBn
                ? "তোমার ডায়াগনস্টিক ফলাফল, লেসন অগ্রগতি, বাস্তব কোড অনুশীলন এবং Skill Graph অনুযায়ী পরবর্তী ধাপ সাজানো হয়েছে।"
                : "Your track, lessons, practice problems, and Skill Graph progress update directly from your real coding and diagnostic work."}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <div
              role="group"
              aria-label="Dashboard language"
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
              href="/student/diagnostic"
              className="inline-flex items-center gap-2 rounded-xl bg-teal-400 px-4 py-2.5 text-[15px] font-semibold text-slate-950 shadow-sm transition hover:bg-teal-300"
            >
              <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
              <span>
                {trackStatus.diagnostic_completed
                  ? isBn
                    ? "নতুন ডায়াগনস্টিক"
                    : "Retake Diagnostic"
                  : isBn
                    ? "৮-ডোমেইন ডায়াগনস্টিক শুরু করো"
                    : "Start 8-Domain Diagnostic"}
              </span>
            </Link>
          </div>
        </div>

        {/* Factual Evidence Counters (Zero Fabricated Percentages) */}
        <div className="mt-6 grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Active Track
            </p>
            <p className="mt-1.5 text-lg font-bold capitalize text-teal-300">
              {trackStatus.selected_track_slug.replaceAll("_", " ")}
            </p>
            <p className="mt-1 text-xs text-slate-400">
              {trackStatus.recommendation_source === "diagnostic_evidence"
                ? "Backed by diagnostic evidence"
                : "Initial onboarding selection"}
            </p>
          </div>
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Guided Lessons Passed
            </p>
            <p className="mt-1.5 text-2xl font-bold text-white">
              {initialDashboard.lessons_completed} /{" "}
              {initialDashboard.lessons_total}
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Requires exercise verification
            </p>
          </div>
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Diagnostics Completed
            </p>
            <p className="mt-1.5 text-2xl font-bold text-white">
              {initialDashboard.diagnostic_sessions_completed}
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Across 8 {activeLanguageLabel} skill domains
            </p>
          </div>
          <div className="rounded-xl border border-slate-700/80 bg-slate-900/70 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Skill Nodes Observed
            </p>
            <p className="mt-1.5 text-2xl font-bold text-white">
              {observedSkills} / {initialDashboard.skill_graph.nodes.length}
            </p>
            <p className="mt-1 text-xs text-slate-400">
              {verifiedSkills} independently verified
            </p>
          </div>
        </div>
      </section>

      {languageOverview ? (
        <LanguageSelector
          accessToken={accessToken}
          initialOverview={languageOverview}
          explanationLanguage={lang}
        />
      ) : null}

      {/* Recommended Next Steps (Explainable Prerequisite-Based Logic) */}
      <section
        aria-label="Recommended next steps"
        className="space-y-4 rounded-2xl border border-indigo-200 bg-white p-6 shadow-sm"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <Sparkles className="h-5 w-5 text-indigo-600" aria-hidden="true" />
            <h2 className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
              {isBn
                ? "তোমার পরবর্তী প্রস্তাবিত ধাপ (Recommended Next)"
                : "Recommended Next Steps"}
            </h2>
          </div>
          <Link
            href="/student/lessons"
            className="text-sm font-semibold text-indigo-700 hover:underline"
          >
            {isBn
              ? `সব ${initialDashboard.lessons_total}টি লেসন দেখো →`
              : `Browse all ${initialDashboard.lessons_total} lessons →`}
          </Link>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {initialDashboard.recommendations.map((rec) => (
            <article
              key={`${rec.recommendation_type}-${rec.target_id}`}
              className="flex flex-col justify-between rounded-xl border border-slate-200 bg-slate-50/70 p-5"
            >
              <div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Badge
                    variant={
                      rec.recommendation_type === "diagnostic_assessment"
                        ? "amber"
                        : rec.recommendation_type === "transfer_challenge"
                          ? "emerald"
                          : "indigo"
                    }
                  >
                    <span className="capitalize">
                      {rec.recommendation_type.replaceAll("_", " ")}
                    </span>
                  </Badge>
                  <span className="text-xs font-medium text-slate-500">
                    Priority #{rec.priority}
                  </span>
                </div>
                <h3 className="mt-2.5 text-lg font-bold text-slate-900">
                  {rec.title}
                </h3>
                <p className="mt-1.5 text-[15px] leading-relaxed text-slate-700">
                  {isBn ? rec.reason_bn : rec.reason_en}
                </p>
                {rec.evidence_factors.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {rec.evidence_factors.map((f) => (
                      <code
                        key={f}
                        className="rounded-md bg-white px-2 py-0.5 text-xs text-slate-600 ring-1 ring-slate-200"
                      >
                        {f}
                      </code>
                    ))}
                  </div>
                ) : null}
              </div>

              <div className="mt-4 pt-2">
                <Link
                  href={rec.href}
                  className="inline-flex items-center gap-2 rounded-xl bg-[#0b1221] px-4 py-2.5 text-[15px] font-semibold text-white transition hover:bg-slate-800"
                >
                  <span>{isBn ? "শুরু করো" : "Open Next Step"}</span>
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* Four Learning Tracks Selection & Evidence Guidance */}
      <section
        aria-label="Four learning tracks"
        className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Compass className="h-4 w-4 text-teal-700" aria-hidden="true" />
            <h2 className="text-base font-bold text-slate-900">
              {isBn
                ? "চারটি লার্নিং ট্র্যাক (Four Learning Levels)"
                : "Four Learning Tracks"}
            </h2>
          </div>
          {trackStatus.recommended_track_slug ? (
            <Badge variant="teal">
              <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
              <span>
                Evidence Recommended:{" "}
                {trackStatus.recommended_track_slug.replaceAll("_", " ")}
              </span>
            </Badge>
          ) : (
            <Badge variant="amber">
              <span>Diagnostic Recommended for Verified Placement</span>
            </Badge>
          )}
        </div>

        <p className="text-xs text-slate-600">
          {trackStatus.recommendation_reason}
        </p>

        {trackError ? (
          <p role="alert" className="text-xs font-medium text-rose-700">
            {trackError}
          </p>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {trackStatus.tracks.map((tr) => {
            const isActive = trackStatus.selected_track_slug === tr.slug;
            const isRecommended = trackStatus.recommended_track_slug === tr.slug;
            return (
              <div
                key={tr.slug}
                className={`flex flex-col justify-between rounded-xl border p-4 transition ${
                  isActive
                    ? "border-indigo-500 bg-indigo-50/40 ring-1 ring-indigo-500"
                    : "border-slate-200 bg-white"
                }`}
              >
                <div>
                  <div className="flex flex-wrap items-center justify-between gap-1">
                    <h3 className="text-sm font-bold text-slate-900">
                      {isBn ? tr.title_bn : tr.title_en}
                    </h3>
                    {isRecommended ? (
                      <Badge variant="teal">Recommended</Badge>
                    ) : null}
                  </div>
                  <p className="mt-1.5 text-xs text-slate-600">
                    {isBn ? tr.summary_bn : tr.summary_en}
                  </p>
                  <p className="mt-2 text-[11px] text-slate-500">
                    {isBn ? tr.target_audience_bn : tr.target_audience_en}
                  </p>
                </div>

                <div className="mt-3">
                  <button
                    type="button"
                    disabled={isActive || savingTrack !== null}
                    onClick={() => {
                      void handleSelectTrack(tr.slug);
                    }}
                    className={`inline-flex w-full items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                      isActive
                        ? "bg-indigo-600 text-white"
                        : "border border-slate-300 bg-white text-slate-800 hover:bg-slate-50"
                    } disabled:cursor-default`}
                  >
                    {savingTrack === tr.slug ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : null}
                    <span>
                      {isActive
                        ? isBn
                          ? "সক্রিয় ট্র্যাক"
                          : "Active Track"
                        : isBn
                          ? "এই ট্র্যাক নির্বাচন করো"
                          : "Select Track"}
                    </span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Prerequisite-Aware Skill Graph */}
      <SkillGraphPanel graph={initialDashboard.skill_graph} language={lang} />

      {/* Phase 6 Adaptive Growth Hub: Daily Plan, Learning DNA, Retention, History */}
      <section aria-label="Adaptive growth tools" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Link
          href="/student/daily-plan"
          className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-indigo-300"
        >
          <div>
            <div className="flex items-center justify-between gap-2">
              <Calendar className="h-4 w-4 text-teal-600" aria-hidden="true" />
              <Badge variant="teal">
                {dailyPlanSummary
                  ? `${dailyPlanSummary.completedTasks}/${dailyPlanSummary.totalTasks}`
                  : isBn
                    ? "আজকের প্ল্যান"
                    : "Today"}
              </Badge>
            </div>
            <h3 className="mt-2.5 text-sm font-bold text-slate-900">
              {isBn ? "অ্যাডাপ্টিভ দৈনিক পরিকল্পনা" : "Adaptive Daily Plan"}
            </h3>
            <p className="mt-1 text-xs text-slate-600">
              {dailyPlanSummary
                ? `${dailyPlanSummary.availableMinutes}m budget · v${dailyPlanSummary.versionNumber}`
                : isBn
                  ? "তোমার সময় ও দক্ষতা অনুযায়ী কাজ"
                  : "Personalized tasks for your time & gaps"}
            </p>
          </div>
          <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-indigo-700">
            {isBn ? "খুলুন" : "Open Plan"}
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </span>
        </Link>

        <Link
          href="/student/dna"
          className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-indigo-300"
        >
          <div>
            <div className="flex items-center justify-between gap-2">
              <Dna className="h-4 w-4 text-indigo-600" aria-hidden="true" />
              <Badge variant="indigo">
                {dnaSummary
                  ? `${dnaSummary.verifiedCount}/${dnaSummary.totalDimensions} verified`
                  : "6 Dimensions"}
              </Badge>
            </div>
            <h3 className="mt-2.5 text-sm font-bold text-slate-900">
              {isBn ? "লার্নিং ডিএনএ" : "Learning DNA"}
            </h3>
            <p className="mt-1 text-xs text-slate-600">
              {isBn
                ? "ট্রেসিং, কোডিং, ডিবাগিং, টেস্টিং, ট্রান্সফার ও রিটেনশন"
                : "Tracing, coding, debugging, testing, transfer & retention"}
            </p>
          </div>
          <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-indigo-700">
            {isBn ? "প্রোফাইল দেখুন" : "View Profile"}
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </span>
        </Link>

        <Link
          href="/student/retention"
          className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-teal-300"
        >
          <div>
            <div className="flex items-center justify-between gap-2">
              <Timer className="h-4 w-4 text-teal-600" aria-hidden="true" />
              <Badge variant={retentionSummary && retentionSummary.dueCount > 0 ? "amber" : "neutral"}>
                {retentionSummary
                  ? `${retentionSummary.dueCount} due · ${retentionSummary.retainedSkillsCount} retained`
                  : "24h Spaced"}
              </Badge>
            </div>
            <h3 className="mt-2.5 text-sm font-bold text-slate-900">
              {isBn ? "রিটেনশন যাচাই" : "Retention Verification"}
            </h3>
            <p className="mt-1 text-xs text-slate-600">
              {isBn
                ? "২৪ ঘণ্টা পর আসল Judge0 যাচাই"
                : "Delayed Judge0 checks (>=24h) before Retained"}
            </p>
          </div>
          <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-indigo-700">
            {isBn ? "যাচাই করুন" : "Check Retention"}
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </span>
        </Link>

        <Link
          href="/student/history"
          className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-indigo-300"
        >
          <div>
            <div className="flex items-center justify-between gap-2">
              <History className="h-4 w-4 text-slate-700" aria-hidden="true" />
              <Badge variant="neutral">
                {isBn ? "টাইমলাইন" : "Timeline"}
              </Badge>
            </div>
            <h3 className="mt-2.5 text-sm font-bold text-slate-900">
              {isBn ? "শেখার ইতিহাস" : "Persistent History"}
            </h3>
            <p className="mt-1 text-xs text-slate-600">
              {isBn
                ? "লেসন, Judge0, মেন্টর, হিন্ট ও ট্রান্সফার অনুসন্ধান"
                : "Searchable log of lessons, Judge0, mentor & skills"}
            </p>
          </div>
          <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-indigo-700">
            {isBn ? "ইতিহাস দেখুন" : "Explore History"}
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </span>
        </Link>
      </section>

      {/* Quick Links to Lessons & Problem Bank */}
      <section className="grid gap-4 sm:grid-cols-2">
        <Link
          href="/student/lessons"
          className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-indigo-300"
        >
          <div className="flex items-center gap-3">
            <BookOpen className="h-5 w-5 text-indigo-600" aria-hidden="true" />
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                {isBn
                  ? `${activeLanguageLabel} গাইডেড লেসনসমূহ (${initialDashboard.lessons_total}টি)`
                  : `${activeLanguageLabel} Guided Lessons (${initialDashboard.lessons_total} Topics)`}
              </h3>
              <p className="text-xs text-slate-600">
                Bilingual concepts, interactive examples &amp; real Judge0
                exercises
              </p>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-slate-400" aria-hidden="true" />
        </Link>

        <Link
          href="/student/problems"
          className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-teal-300"
        >
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-teal-600" aria-hidden="true" />
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                {isBn
                  ? "প্রবলেম ব্যাংক ও Socratic AI ডিবাগার"
                  : "Problem Bank & Socratic AI Debugger"}
              </h3>
              <p className="text-xs text-slate-600">
                Real code execution, error diagnosis &amp; transfer checks
              </p>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-slate-400" aria-hidden="true" />
        </Link>
      </section>

      {classroomSummary ? (
        <section
          aria-label="Classes and assignments overview"
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                {isBn ? "আমার ক্লাস ও অ্যাসাইনমেন্ট" : "My Classes & Assignments"}
              </h2>
              <p className="text-xs text-slate-600">
                {classroomSummary.enrolledCount} active class(es) ·{" "}
                {classroomSummary.totalAssignmentsCount} assignment(s) (
                {classroomSummary.pendingAssignmentsCount} in progress)
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Link
                href="/student/classes"
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                {isBn ? "ক্লাস দেখুন" : "View Classes"}
              </Link>
              <Link
                href="/student/assignments"
                className="rounded-lg bg-[#0b1221] px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-800"
              >
                {isBn ? "অ্যাসাইনমেন্ট" : "Open Assignments"}
              </Link>
            </div>
          </div>

          {classroomSummary.recentClasses.length > 0 ? (
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              {classroomSummary.recentClasses.map((cls) => (
                <Link
                  key={cls.courseId}
                  href="/student/classes"
                  className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 transition hover:border-teal-300"
                >
                  <span className="font-mono text-xs font-bold text-indigo-700">
                    {cls.code}
                  </span>
                  <p className="mt-1 truncate text-sm font-semibold text-slate-900">
                    {cls.title}
                  </p>
                  <p className="mt-0.5 text-[11px] capitalize text-slate-500">
                    Status: {cls.status}
                  </p>
                </Link>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
