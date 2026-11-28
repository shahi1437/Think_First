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
import { DebuggingTimelinePanel } from "@/features/growth/debugging-timeline-panel";
import { VerifiedProgressPanel } from "@/features/growth/verified-progress-panel";
import { PersonalizedLearningHub } from "@/features/learning/personalized-learning-hub";
import { SkillGraphPanel } from "@/features/learning/skill-graph-panel";
import { selectLearningTrack } from "@/lib/api-client";
import { getLanguageDisplayName } from "@/lib/languages";
import type {
  DebuggingTimelineResponseView,
  VerifiedLearningProgressView,
} from "@/types/growth";
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
  verifiedProgress?: VerifiedLearningProgressView | null;
  debuggingTimeline?: DebuggingTimelineResponseView | null;
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
  verifiedProgress = null,
  debuggingTimeline = null,
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
  const journey = initialDashboard.journey ?? null;
  const primaryAction = journey?.primary_action ?? null;
  const resumeActivity =
    journey?.resume_activity &&
    primaryAction &&
    journey.resume_activity.href !== primaryAction.href
      ? journey.resume_activity
      : null;
  const fallbackRec = initialDashboard.recommendations[0] ?? null;
  const continueHref = primaryAction?.href ?? fallbackRec?.href ?? "/student/lessons";
  const continueTitle = primaryAction
    ? isBn
      ? primaryAction.title_bn
      : primaryAction.title_en
    : (fallbackRec?.title ?? `Continue ${activeLanguageLabel} Learning`);
  const continueReason = primaryAction
    ? isBn
      ? primaryAction.reason_bn
      : primaryAction.reason_en
    : fallbackRec
      ? isBn
        ? fallbackRec.reason_bn
        : fallbackRec.reason_en
      : `Continue your structured ${activeLanguageLabel} learning track.`;
  const continueCtaLabel = primaryAction
    ? isBn
      ? primaryAction.cta_label_bn
      : primaryAction.cta_label_en
    : isBn
      ? "শেখা চালিয়ে যাও"
      : "Continue Learning";
  const lessonPct =
    initialDashboard.lessons_total > 0
      ? Math.round(
          (initialDashboard.lessons_completed / initialDashboard.lessons_total) *
            100,
        )
      : 0;
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
    <div className="tf-animate-enter space-y-6" lang={lang}>
      {/* Editorial Workspace Header + Authoritative Continue Learning Card */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-7">
        <div className="space-y-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold text-teal-700">
                {isBn
                  ? "অ্যাডাপ্টিভ লার্নিং ড্যাশবোর্ড"
                  : "Student Learning Workspace"}{" "}
                · {activeLanguageLabel}
              </p>
              <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
                {isBn ? `স্বাগতম, ${studentName}` : `Welcome back, ${studentName}`}
              </h1>
              <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-[15px]">
                {isBn
                  ? "তোমার ডায়াগনস্টিক ফলাফল, লেসন অগ্রগতি, বাস্তব কোড অনুশীলন এবং Skill Graph অনুযায়ী পরবর্তী সেরা ধাপ নির্ধারিত হয়েছে।"
                  : "Your next step is computed directly from real code execution, lesson progress, class deadlines, and your Skill Graph."}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div
                role="group"
                aria-label="Dashboard language"
                className="inline-flex rounded-lg border border-slate-200 bg-slate-100/80 p-0.5 text-xs"
              >
                <button
                  type="button"
                  onClick={() => setLang("en")}
                  aria-pressed={lang === "en"}
                  className={`rounded-md px-2.5 py-1.5 font-semibold transition-colors ${
                    lang === "en"
                      ? "bg-[#0b1221] text-white"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  English
                </button>
                <button
                  type="button"
                  onClick={() => setLang("bn")}
                  aria-pressed={lang === "bn"}
                  className={`rounded-md px-2.5 py-1.5 font-semibold transition-colors ${
                    lang === "bn"
                      ? "bg-[#0b1221] text-white"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  বাংলা
                </button>
              </div>

              <Link
                href="/student/diagnostic"
                className="tf-btn-press inline-flex min-h-[38px] items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-800 transition-colors hover:border-slate-400 hover:bg-slate-50"
              >
                <ClipboardCheck className="h-4 w-4 text-teal-700" aria-hidden="true" />
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

          {/* Primary Authoritative Action: CONTINUE LEARNING */}
          <div
            data-testid="continue-learning-card"
            className={`tf-scale-in rounded-xl border p-5 sm:p-6 ${
              primaryAction?.urgency === "urgent"
                ? "border-amber-300 bg-amber-50/70"
                : "border-slate-800 bg-[#0b1221] text-white"
            }`}
          >
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-0.5 text-xs font-semibold ${
                      primaryAction?.urgency === "urgent"
                        ? "bg-amber-600 text-white"
                        : "border border-teal-400/30 bg-teal-400/15 text-teal-300"
                    }`}
                  >
                    <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                    <span>
                      {primaryAction?.urgency === "urgent"
                        ? isBn
                          ? "জরুরি পরবর্তী ধাপ · Continue Learning"
                          : "Priority Deadline · Continue Learning"
                        : isBn
                          ? "এখন কী শিখবে? · Continue Learning"
                          : "Recommended Next · Continue Learning"}
                    </span>
                  </span>
                  {primaryAction?.estimated_minutes ? (
                    <span
                      className={`text-xs font-medium tabular-nums ${
                        primaryAction.urgency === "urgent"
                          ? "text-amber-900"
                          : "text-slate-300"
                      }`}
                    >
                      ~{primaryAction.estimated_minutes} min
                    </span>
                  ) : null}
                </div>
                <h2
                  className={`text-lg font-bold sm:text-xl ${
                    primaryAction?.urgency === "urgent"
                      ? "text-slate-950"
                      : "text-white"
                  }`}
                >
                  {continueTitle}
                </h2>
                <p
                  className={`max-w-2xl text-sm leading-relaxed ${
                    primaryAction?.urgency === "urgent"
                      ? "text-slate-700"
                      : "text-slate-300"
                  }`}
                >
                  {continueReason}
                </p>
                {primaryAction && primaryAction.evidence_factors.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {primaryAction.evidence_factors.map((factor) => (
                      <code
                        key={factor}
                        className={`rounded px-2 py-0.5 text-[11px] ${
                          primaryAction.urgency === "urgent"
                            ? "border border-amber-200 bg-white text-amber-900"
                            : "border border-slate-700 bg-slate-900 text-teal-200"
                        }`}
                      >
                        {factor}
                      </code>
                    ))}
                  </div>
                ) : null}
              </div>

              <div className="flex shrink-0 flex-wrap items-center gap-2.5">
                <Link
                  href={continueHref}
                  data-testid="continue-learning-cta"
                  className={`tf-btn-press inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold transition-colors ${
                    primaryAction?.urgency === "urgent"
                      ? "bg-amber-700 text-white hover:bg-amber-800"
                      : "bg-teal-400 text-slate-950 hover:bg-teal-300"
                  }`}
                >
                  <span>{continueCtaLabel}</span>
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </div>
            </div>

            {/* Beginner Foundation Path Progress Strip */}
            {journey &&
            (journey.journey_stage === "foundation_lessons" ||
              journey.journey_stage === "readiness_check") ? (
              <div
                className={`mt-4 border-t pt-4 ${
                  primaryAction?.urgency === "urgent"
                    ? "border-amber-200"
                    : "border-slate-800"
                }`}
              >
                <div
                  className={`flex flex-wrap items-center justify-between gap-2 text-xs font-medium tabular-nums ${
                    primaryAction?.urgency === "urgent"
                      ? "text-amber-900"
                      : "text-slate-300"
                  }`}
                >
                  <span>
                    {isBn
                      ? `নতুনদের ফাউন্ডেশন ধাপ: ${journey.foundation_lessons_completed}/${journey.foundation_lessons_target} প্রাথমিক লেসন → সংক্ষিপ্ত প্রস্তুতি যাচাই`
                      : `Beginner Foundation Path: ${journey.foundation_lessons_completed}/${journey.foundation_lessons_target} intro lessons → Short Readiness Check`}
                  </span>
                  <span
                    className={
                      primaryAction?.urgency === "urgent"
                        ? "font-semibold text-amber-800"
                        : "font-semibold text-teal-300"
                    }
                  >
                    {journey.readiness_check_unlocked
                      ? isBn
                        ? "প্রস্তুতি যাচাই আনলকড ✓"
                        : "Readiness Check Unlocked ✓"
                      : isBn
                        ? "ধাপে ধাপে এগোও"
                        : "Step-by-step gentle start"}
                  </span>
                </div>
                <div
                  className={`mt-2 h-1.5 w-full overflow-hidden rounded-full ${
                    primaryAction?.urgency === "urgent"
                      ? "bg-amber-200"
                      : "bg-slate-800"
                  }`}
                >
                  <div
                    className="tf-progress-fill h-full rounded-full bg-teal-400"
                    style={{
                      width: `${Math.min(
                        100,
                        Math.round(
                          (journey.foundation_lessons_completed /
                            Math.max(journey.foundation_lessons_target, 1)) *
                            100,
                        ),
                      )}%`,
                    }}
                  />
                </div>
              </div>
            ) : null}

            {/* Optional Resume Last Activity bar when distinct from primary CTA */}
            {resumeActivity ? (
              <div
                className={`mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-3 ${
                  primaryAction?.urgency === "urgent"
                    ? "border-amber-200 bg-white"
                    : "border-slate-800 bg-slate-900/80"
                }`}
              >
                <div>
                  <p
                    className={`text-xs font-medium ${
                      primaryAction?.urgency === "urgent"
                        ? "text-slate-500"
                        : "text-teal-300"
                    }`}
                  >
                    {isBn ? "আগের অসমাপ্ত কাজ চালিয়ে যাও" : "Resume Last Activity"}
                  </p>
                  <p
                    className={`text-sm font-semibold ${
                      primaryAction?.urgency === "urgent"
                        ? "text-slate-900"
                        : "text-white"
                    }`}
                  >
                    {isBn ? resumeActivity.title_bn : resumeActivity.title_en}
                  </p>
                </div>
                <Link
                  href={resumeActivity.href}
                  data-testid="resume-activity-cta"
                  className={`tf-btn-press inline-flex min-h-[38px] items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors ${
                    primaryAction?.urgency === "urgent"
                      ? "border-slate-300 bg-slate-50 text-slate-900 hover:bg-slate-100"
                      : "border-slate-700 bg-slate-800 text-slate-100 hover:bg-slate-700"
                  }`}
                >
                  <span>
                    {isBn
                      ? resumeActivity.cta_label_bn
                      : resumeActivity.cta_label_en}
                  </span>
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                </Link>
              </div>
            ) : null}
          </div>

          {/* Factual Evidence Counters (Zero Fabricated Percentages) */}
          <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-[#f7f8fa] p-4">
              <p className="text-xs font-medium text-slate-500">Active Track</p>
              <p className="mt-1 text-base font-bold capitalize text-teal-800">
                {trackStatus.selected_track_slug.replaceAll("_", " ")}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {trackStatus.recommendation_source === "diagnostic_evidence"
                  ? "Backed by diagnostic evidence"
                  : "Initial onboarding selection"}
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-[#f7f8fa] p-4">
              <p className="text-xs font-medium text-slate-500">
                Guided Lessons Passed
              </p>
              <p className="mt-1 text-2xl font-bold text-slate-950 tabular-nums">
                {initialDashboard.lessons_completed} /{" "}
                {initialDashboard.lessons_total}
              </p>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                <div
                  className="tf-progress-fill h-full rounded-full bg-teal-600"
                  style={{ width: `${lessonPct}%` }}
                />
              </div>
              <p className="mt-1.5 text-xs text-slate-500">
                Requires exercise verification
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-[#f7f8fa] p-4">
              <p className="text-xs font-medium text-slate-500">
                Diagnostics Completed
              </p>
              <p className="mt-1 text-2xl font-bold text-slate-950 tabular-nums">
                {initialDashboard.diagnostic_sessions_completed}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Across {activeLanguageLabel} skill domains
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-[#f7f8fa] p-4">
              <p className="text-xs font-medium text-slate-500">
                Skill Nodes Observed
              </p>
              <p className="mt-1 text-2xl font-bold text-slate-950 tabular-nums">
                {observedSkills} / {initialDashboard.skill_graph.nodes.length}
              </p>
              <p className="mt-1 text-xs text-slate-500 tabular-nums">
                {verifiedSkills} independently verified
              </p>
            </div>
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

      {/* Phase 11 Feature 2: Verified Learning Progress */}
      {verifiedProgress ? (
        <VerifiedProgressPanel progress={verifiedProgress} language={lang} />
      ) : null}

      {/* Phase 9: Unified 5-Question Personalized Learning Coach */}
      <PersonalizedLearningHub
        dashboard={initialDashboard}
        verifiedProgress={verifiedProgress}
        retentionSummary={retentionSummary}
        dailyPlanSummary={dailyPlanSummary}
        language={lang}
      />

      {/* Phase 11 Feature 1 Preview: AI Debugging Timeline */}
      {debuggingTimeline ? (
        <DebuggingTimelinePanel
          timeline={debuggingTimeline}
          language={lang}
          compact
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
              className="tf-card-interactive flex flex-col justify-between rounded-2xl border border-slate-200 bg-slate-50/70 p-5 hover:border-indigo-300 hover:bg-white hover:shadow-md"
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
                <p className="mt-1.5 text-base leading-relaxed text-slate-700">
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
                  className="tf-btn-press inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-[#0b1221] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 sm:text-[15px]"
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

        <p className="text-sm leading-relaxed text-slate-600">
          {trackStatus.recommendation_reason}
        </p>

        {trackError ? (
          <p role="alert" className="text-sm font-medium text-rose-700">
            {trackError}
          </p>
        ) : null}

        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
          {trackStatus.tracks.map((tr) => {
            const isActive = trackStatus.selected_track_slug === tr.slug;
            const isRecommended = trackStatus.recommended_track_slug === tr.slug;
            return (
              <div
                key={tr.slug}
                className={`tf-card-interactive flex flex-col justify-between rounded-xl border p-4 ${
                  isActive
                    ? "border-indigo-500 bg-indigo-50/40 ring-1 ring-indigo-500"
                    : "border-slate-200 bg-white hover:border-indigo-300"
                }`}
              >
                <div>
                  <div className="flex flex-wrap items-center justify-between gap-1">
                    <h3 className="text-base font-bold text-slate-900">
                      {isBn ? tr.title_bn : tr.title_en}
                    </h3>
                    {isRecommended ? (
                      <Badge variant="teal">Recommended</Badge>
                    ) : null}
                  </div>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-600">
                    {isBn ? tr.summary_bn : tr.summary_en}
                  </p>
                  <p className="mt-2 text-xs text-slate-500">
                    {isBn ? tr.target_audience_bn : tr.target_audience_en}
                  </p>
                </div>

                <div className="mt-3.5">
                  <button
                    type="button"
                    disabled={isActive || savingTrack !== null}
                    onClick={() => {
                      void handleSelectTrack(tr.slug);
                    }}
                    className={`tf-btn-press inline-flex min-h-[40px] w-full items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold transition ${
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
