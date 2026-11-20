"use client";

import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ClipboardCheck,
  Compass,
  Loader2,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { SkillGraphPanel } from "@/features/learning/skill-graph-panel";
import { selectLearningTrack } from "@/lib/api-client";
import type {
  LearningDashboardView,
  StudentTrackStatus,
  TrackSlug,
} from "@/types/learning";

interface LearningDashboardClientProps {
  accessToken: string;
  studentName: string;
  initialDashboard: LearningDashboardView;
  initialLanguage?: "en" | "bn";
}

export function LearningDashboardClient({
  accessToken,
  studentName,
  initialDashboard,
  initialLanguage = "en",
}: LearningDashboardClientProps) {
  const [lang, setLang] = useState<"en" | "bn">(initialLanguage);
  const [trackStatus, setTrackStatus] = useState<StudentTrackStatus>(
    initialDashboard.track_status,
  );
  const [savingTrack, setSavingTrack] = useState<TrackSlug | null>(null);
  const [trackError, setTrackError] = useState<string | null>(null);

  const isBn = lang === "bn";
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
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-teal-700">
              {isBn ? "অ্যাডাপ্টিভ লার্নিং ড্যাশবোর্ড" : "Adaptive Learning Dashboard"}
            </p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900">
              {isBn ? `স্বাগতম, ${studentName}` : `Welcome back, ${studentName}`}
            </h1>
            <p className="mt-1.5 max-w-2xl text-sm text-slate-600">
              {isBn
                ? "তোমার ডায়াগনস্টিক প্রমাণ, লেসন অগ্রগতি, Judge0 কোড এক্সিকিউশন এবং Skill Graph অনুযায়ী পরবর্তী ধাপ সাজানো হয়েছে।"
                : "Your track, lessons, and Skill Graph are grounded strictly in real diagnostic, Judge0 execution, and transfer verification evidence."}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div
              role="group"
              aria-label="Dashboard language"
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

            <Link
              href="/student/diagnostic"
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-indigo-500"
            >
              <ClipboardCheck className="h-3.5 w-3.5" aria-hidden="true" />
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
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Active Track
            </p>
            <p className="mt-1 text-sm font-bold capitalize text-indigo-900">
              {trackStatus.selected_track_slug.replaceAll("_", " ")}
            </p>
            <p className="mt-0.5 text-[11px] text-slate-500">
              {trackStatus.recommendation_source === "diagnostic_evidence"
                ? "Backed by diagnostic evidence"
                : "Initial onboarding selection"}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Guided Lessons Passed
            </p>
            <p className="mt-1 text-lg font-bold text-slate-900">
              {initialDashboard.lessons_completed} /{" "}
              {initialDashboard.lessons_total}
            </p>
            <p className="text-[11px] text-slate-500">
              Requires Judge0 exercise pass
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Diagnostics Completed
            </p>
            <p className="mt-1 text-lg font-bold text-slate-900">
              {initialDashboard.diagnostic_sessions_completed}
            </p>
            <p className="text-[11px] text-slate-500">
              Across 8 Python skill domains
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Skill Nodes Observed
            </p>
            <p className="mt-1 text-lg font-bold text-slate-900">
              {observedSkills} / {initialDashboard.skill_graph.nodes.length}
            </p>
            <p className="text-[11px] text-slate-500">
              {verifiedSkills} independently verified
            </p>
          </div>
        </div>
      </section>

      {/* Recommended Next Steps (Explainable Prerequisite-Based Logic) */}
      <section
        aria-label="Recommended next steps"
        className="space-y-3 rounded-2xl border border-indigo-200 bg-white p-5 shadow-sm"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-600" aria-hidden="true" />
            <h2 className="text-base font-bold text-slate-900">
              {isBn
                ? "তোমার পরবর্তী প্রস্তাবিত ধাপ (Recommended Next)"
                : "Recommended Next Steps"}
            </h2>
          </div>
          <Link
            href="/student/lessons"
            className="text-xs font-semibold text-indigo-700 hover:underline"
          >
            {isBn ? "সব ৮টি লেসন দেখো →" : "Browse all 8 lessons →"}
          </Link>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          {initialDashboard.recommendations.map((rec) => (
            <article
              key={`${rec.recommendation_type}-${rec.target_id}`}
              className="flex flex-col justify-between rounded-xl border border-slate-200 bg-slate-50/60 p-4"
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
                  <span className="text-[11px] font-medium text-slate-500">
                    Priority #{rec.priority}
                  </span>
                </div>
                <h3 className="mt-2 text-sm font-bold text-slate-900">
                  {rec.title}
                </h3>
                <p className="mt-1 text-xs leading-relaxed text-slate-700">
                  {isBn ? rec.reason_bn : rec.reason_en}
                </p>
                {rec.evidence_factors.length > 0 ? (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {rec.evidence_factors.map((f) => (
                      <code
                        key={f}
                        className="rounded bg-white px-1.5 py-0.5 text-[10px] text-slate-600 ring-1 ring-slate-200"
                      >
                        {f}
                      </code>
                    ))}
                  </div>
                ) : null}
              </div>

              <div className="mt-3 pt-2">
                <Link
                  href={rec.href}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-slate-800"
                >
                  <span>{isBn ? "শুরু করো" : "Open Next Step"}</span>
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
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
                  ? "বিগিনার Python লেসনসমূহ"
                  : "Beginner Python Lessons (8 Topics)"}
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
                Real Judge0 execution, ML diagnosis, RAG citations &amp;
                transfer checks
              </p>
            </div>
          </div>
          <ArrowRight className="h-4 w-4 text-slate-400" aria-hidden="true" />
        </Link>
      </section>
    </div>
  );
}
