"use client";

import {
  Award,
  Bug,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Code2,
  ExternalLink,
  Flag,
  Lightbulb,
  Play,
  PlayCircle,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { computeLineDiff } from "@/lib/code-diff";
import { formatUtcDateTime } from "@/lib/format-date";
import { getLanguageDisplayName } from "@/lib/languages";
import type {
  DebuggingJourneyOutcome,
  DebuggingStepKind,
  DebuggingTimelineResponseView,
  DebuggingTimelineStepView,
} from "@/types/growth";

interface DebuggingTimelinePanelProps {
  timeline: DebuggingTimelineResponseView;
  language?: "en" | "bn";
  compact?: boolean;
}

const STEP_META: Record<
  DebuggingStepKind,
  {
    label: string;
    dotClass: string;
    Icon: typeof Flag;
  }
> = {
  problem_started: {
    label: "Problem",
    dotClass: "border-slate-300 bg-slate-100 text-slate-700",
    Icon: Flag,
  },
  initial_attempt: {
    label: "Initial Attempt",
    dotClass: "border-slate-300 bg-white text-slate-700",
    Icon: PlayCircle,
  },
  error_diagnosed: {
    label: "ML Diagnosis",
    dotClass: "border-rose-200 bg-rose-50 text-rose-700",
    Icon: Bug,
  },
  ai_hint: {
    label: "AI Hint",
    dotClass: "border-amber-200 bg-amber-50 text-amber-800",
    Icon: Lightbulb,
  },
  student_correction: {
    label: "Correction",
    dotClass: "border-sky-200 bg-sky-50 text-sky-800",
    Icon: Wrench,
  },
  successful_execution: {
    label: "Accepted",
    dotClass: "border-emerald-200 bg-emerald-50 text-emerald-800",
    Icon: CheckCircle2,
  },
  learning_outcome: {
    label: "Outcome",
    dotClass: "border-teal-200 bg-teal-50 text-teal-800",
    Icon: Award,
  },
};

const OUTCOME_BADGE: Record<
  DebuggingJourneyOutcome,
  { label: string; className: string }
> = {
  verified_transfer: {
    label: "Verified Transfer",
    className: "border-emerald-200 bg-emerald-50 text-emerald-800",
  },
  solved: {
    label: "Solved",
    className: "border-teal-200 bg-teal-50 text-teal-800",
  },
  in_progress: {
    label: "In Progress",
    className: "border-amber-200 bg-amber-50 text-amber-800",
  },
};

function findPreviousCode(
  steps: DebuggingTimelineStepView[],
  currentIndex: number,
): string | null {
  for (let i = currentIndex - 1; i >= 0; i -= 1) {
    if (steps[i]?.code_excerpt) {
      return steps[i].code_excerpt;
    }
  }
  return null;
}

export function DebuggingTimelinePanel({
  timeline,
  language = "en",
  compact = false,
}: DebuggingTimelinePanelProps) {
  const isBn = language === "bn";
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>(() =>
    timeline.journeys.length > 0
      ? { [timeline.journeys[0].problem_id]: true }
      : {},
  );
  const [replayModeById, setReplayModeById] = useState<Record<string, boolean>>(
    {},
  );
  const [replayStepById, setReplayStepById] = useState<Record<string, number>>(
    {},
  );

  const verifiedTransferCount = timeline.journeys.filter(
    (j) => j.outcome_status === "verified_transfer",
  ).length;
  const visibleJourneys = compact
    ? timeline.journeys.slice(0, 2)
    : timeline.journeys;

  function toggleJourney(problemId: string) {
    setExpandedIds((prev) => ({ ...prev, [problemId]: !prev[problemId] }));
  }

  function setReplayMode(problemId: string, enabled: boolean) {
    setExpandedIds((prev) => ({ ...prev, [problemId]: true }));
    setReplayModeById((prev) => ({ ...prev, [problemId]: enabled }));
    setReplayStepById((prev) => ({
      ...prev,
      [problemId]: prev[problemId] ?? 0,
    }));
  }

  function setStepIndex(problemId: string, idx: number, maxLen: number) {
    const clamped = Math.max(0, Math.min(maxLen - 1, idx));
    setReplayStepById((prev) => ({ ...prev, [problemId]: clamped }));
  }

  return (
    <section
      aria-label="AI Debugging Timeline"
      data-testid="ai-debugging-timeline"
      className="rounded-2xl border border-slate-200 bg-white p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <p className="text-xs font-semibold text-teal-700">
            {isBn
              ? "AI ডিবাগিং যাত্রা ও রিপ্লে"
              : "AI Debugging Timeline & Chronological Replay"}
          </p>
          <h2 className="mt-1 text-lg font-bold tracking-tight text-slate-950">
            {isBn
              ? "সমস্যা থেকে সমাধান পর্যন্ত তোমার ডিবাগিং ধাপসমূহ"
              : "How You Diagnosed and Solved Each Problem"}
          </h2>
          <p className="mt-1 text-xs text-slate-600">
            {isBn
              ? "আসল স্যান্ডবক্স রান, ML ত্রুটি বিশ্লেষণ, AI হিন্ট এবং কোড সংশোধন থেকে তৈরি।"
              : "Reconstructed strictly from persisted sandbox runs, ML error diagnoses, progressive AI hints, code revisions, and transfer checks."}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs tabular-nums">
          <span className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 font-medium text-slate-700">
            {timeline.total_journeys} problem(s)
          </span>
          <span className="rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1 font-medium text-emerald-800">
            {timeline.solved_journeys} solved
          </span>
          {verifiedTransferCount > 0 ? (
            <span className="rounded-md border border-teal-200 bg-teal-50 px-2.5 py-1 font-medium text-teal-800">
              {verifiedTransferCount} verified transfer
            </span>
          ) : null}
          {compact ? (
            <Link
              href="/student/history"
              className="font-semibold text-teal-700 hover:underline"
            >
              Open Full Timeline →
            </Link>
          ) : null}
        </div>
      </div>

      {visibleJourneys.length === 0 ? (
        <div className="mt-5 rounded-xl border border-dashed border-slate-300 bg-[#f7f8fa] p-6 text-center">
          <Code2
            className="mx-auto h-6 w-6 text-slate-400"
            aria-hidden="true"
          />
          <p className="mt-2 text-sm font-semibold text-slate-800">
            {isBn
              ? "এখনো কোনো ডিবাগিং যাত্রা রেকর্ড হয়নি"
              : "No debugging journeys recorded yet"}
          </p>
          <p className="mt-1 text-xs text-slate-600">
            Run or submit code in the Problem Bank to capture your real
            attempt → diagnosis → AI hint → fix timeline.
          </p>
          <Link
            href="/student/problems"
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-[#0b1221] px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            Open Problem Bank
          </Link>
        </div>
      ) : (
        <div className="mt-5 space-y-4">
          {visibleJourneys.map((journey) => {
            const expanded = Boolean(expandedIds[journey.problem_id]);
            const isReplay = Boolean(replayModeById[journey.problem_id]);
            const currentIdx = Math.min(
              replayStepById[journey.problem_id] ?? 0,
              Math.max(0, journey.steps.length - 1),
            );
            const currentStep = journey.steps[currentIdx];
            const prevCode = currentStep?.code_excerpt
              ? findPreviousCode(journey.steps, currentIdx)
              : null;
            const stepDiff =
              currentStep?.code_excerpt &&
                prevCode &&
                prevCode !== currentStep.code_excerpt
                ? computeLineDiff(prevCode, currentStep.code_excerpt)
                : null;
            const outcome = OUTCOME_BADGE[journey.outcome_status];

            return (
              <article
                key={journey.problem_id}
                data-testid="debugging-journey-card"
                className="overflow-hidden rounded-xl border border-slate-200 bg-[#f7f8fa]/70"
              >
                <div className="flex flex-wrap items-center justify-between gap-3 bg-white px-4 py-3.5">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`inline-flex rounded-md border px-2 py-0.5 text-[11px] font-semibold ${outcome.className}`}
                      >
                        {outcome.label}
                      </span>
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-700">
                        {getLanguageDisplayName(journey.language_slug)}
                      </span>
                      <span className="text-[11px] text-slate-500 tabular-nums">
                        {journey.attempts_count} run(s) ·{" "}
                        {journey.diagnoses_count} diagnosis ·{" "}
                        {journey.hints_used} hint(s)
                      </span>
                    </div>
                    <h3 className="mt-1 text-sm font-bold text-slate-950">
                      {journey.problem_title}
                    </h3>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {journey.steps.length > 1 ? (
                      <button
                        type="button"
                        data-testid="debugging-replay-toggle"
                        aria-pressed={isReplay}
                        onClick={() =>
                          setReplayMode(journey.problem_id, !isReplay)
                        }
                        className={`inline-flex items-center gap-1 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition-colors ${isReplay
                          ? "border-teal-700 bg-teal-700 text-white"
                          : "border-teal-200 bg-teal-50 text-teal-800 hover:bg-teal-100"
                          }`}
                      >
                        <Play className="h-3 w-3" aria-hidden="true" />
                        <span>{isReplay ? "List View" : "Replay Journey"}</span>
                      </button>
                    ) : null}
                    <Link
                      href={journey.href}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                    >
                      <span>Open Problem</span>
                      <ExternalLink className="h-3 w-3" aria-hidden="true" />
                    </Link>
                    <button
                      type="button"
                      onClick={() => toggleJourney(journey.problem_id)}
                      aria-expanded={expanded}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
                    >
                      <span>
                        {expanded
                          ? "Hide steps"
                          : `View ${journey.steps.length} steps`}
                      </span>
                      {expanded ? (
                        <ChevronUp className="h-3.5 w-3.5" aria-hidden="true" />
                      ) : (
                        <ChevronDown
                          className="h-3.5 w-3.5"
                          aria-hidden="true"
                        />
                      )}
                    </button>
                  </div>
                </div>

                {expanded && isReplay && currentStep ? (
                  <div
                    data-testid="debugging-replay-stage"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "ArrowLeft") {
                        setStepIndex(
                          journey.problem_id,
                          currentIdx - 1,
                          journey.steps.length,
                        );
                      } else if (e.key === "ArrowRight") {
                        setStepIndex(
                          journey.problem_id,
                          currentIdx + 1,
                          journey.steps.length,
                        );
                      }
                    }}
                    className="space-y-4 border-t border-slate-200 bg-white p-4 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-teal-600/30"
                  >
                    {/* Step Scrubber Bar */}
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-slate-700 tabular-nums">
                        Step {currentIdx + 1} of {journey.steps.length} ·{" "}
                        {STEP_META[currentStep.step_kind].label}
                      </span>
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          disabled={currentIdx === 0}
                          onClick={() =>
                            setStepIndex(
                              journey.problem_id,
                              currentIdx - 1,
                              journey.steps.length,
                            )
                          }
                          aria-label="Previous debugging step"
                          className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
                        >
                          <ChevronLeft className="h-3.5 w-3.5" />
                          Prev
                        </button>
                        <button
                          type="button"
                          disabled={currentIdx >= journey.steps.length - 1}
                          onClick={() =>
                            setStepIndex(
                              journey.problem_id,
                              currentIdx + 1,
                              journey.steps.length,
                            )
                          }
                          aria-label="Next debugging step"
                          className="inline-flex items-center gap-1 rounded-md bg-[#0b1221] px-2.5 py-1 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-40"
                        >
                          Next
                          <ChevronRight className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Clickable Chronological Step Pills */}
                    <div className="flex flex-wrap gap-1.5" role="tablist">
                      {journey.steps.map((st, idx) => (
                        <button
                          key={st.id}
                          type="button"
                          role="tab"
                          aria-selected={idx === currentIdx}
                          onClick={() =>
                            setStepIndex(
                              journey.problem_id,
                              idx,
                              journey.steps.length,
                            )
                          }
                          className={`rounded-md border px-2 py-1 text-[11px] font-medium tabular-nums transition-colors ${idx === currentIdx
                            ? "border-teal-700 bg-teal-700 text-white"
                            : idx < currentIdx
                              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                              : "border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100"
                            }`}
                        >
                          {idx + 1}. {STEP_META[st.step_kind].label}
                        </button>
                      ))}
                    </div>

                    {/* Active Step Detail Card */}
                    <div
                      aria-live="polite"
                      className="rounded-xl border border-slate-200 bg-[#f7f8fa] p-4"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <h4 className="text-sm font-bold text-slate-950">
                          {currentStep.title}
                        </h4>
                        <time className="text-[11px] text-slate-500 tabular-nums">
                          {formatUtcDateTime(currentStep.occurred_at)}
                        </time>
                      </div>
                      <p className="mt-1.5 text-xs leading-relaxed text-slate-700">
                        {currentStep.detail}
                      </p>

                      {stepDiff ? (
                        <div className="mt-3 space-y-1.5">
                          <div className="flex items-center justify-between text-[11px] font-medium text-slate-600 tabular-nums">
                            <span>Code diff vs. previous snapshot</span>
                            <span>
                              <span className="text-emerald-700">
                                +{stepDiff.addedCount}
                              </span>{" "}
                              /{" "}
                              <span className="text-rose-700">
                                -{stepDiff.removedCount}
                              </span>
                            </span>
                          </div>
                          <pre className="overflow-x-auto rounded-lg border border-slate-200 bg-slate-950 p-3 font-mono text-[11px] leading-relaxed">
                            {stepDiff.lines.map((ln, lIdx) => (
                              <div
                                key={`${ln.kind}-${lIdx}`}
                                className={
                                  ln.kind === "added"
                                    ? "bg-emerald-950/70 text-emerald-200"
                                    : ln.kind === "removed"
                                      ? "bg-rose-950/70 text-rose-200"
                                      : "text-slate-300"
                                }
                              >
                                <span className="mr-2 inline-block w-3 select-none opacity-70">
                                  {ln.kind === "added"
                                    ? "+"
                                    : ln.kind === "removed"
                                      ? "-"
                                      : " "}
                                </span>
                                {ln.text}
                              </div>
                            ))}
                          </pre>
                        </div>
                      ) : currentStep.code_excerpt ? (
                        <pre className="mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-slate-950 px-3 py-2 font-mono text-[11px] leading-relaxed text-slate-100">
                          <code>{currentStep.code_excerpt}</code>
                        </pre>
                      ) : null}
                    </div>
                  </div>
                ) : expanded ? (
                  <ol className="space-y-3 border-t border-slate-200 px-4 py-4">
                    {journey.steps.map((step, idx) => {
                      const meta = STEP_META[step.step_kind];
                      const StepIcon = meta.Icon;
                      return (
                        <li
                          key={step.id}
                          data-testid="debugging-timeline-step"
                          className="relative flex gap-3"
                        >
                          <div className="flex flex-col items-center">
                            <span
                              className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border ${meta.dotClass}`}
                            >
                              <StepIcon
                                className="h-3.5 w-3.5"
                                aria-hidden="true"
                              />
                            </span>
                            {idx < journey.steps.length - 1 ? (
                              <span
                                aria-hidden="true"
                                className="mt-1 w-px flex-1 bg-slate-200"
                              />
                            ) : null}
                          </div>

                          <div className="min-w-0 flex-1 pb-2">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="text-xs font-semibold text-slate-900">
                                  {step.title}
                                </span>
                                <span className="rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
                                  {meta.label}
                                </span>
                              </div>
                              <time className="text-[11px] text-slate-400 tabular-nums">
                                {formatUtcDateTime(step.occurred_at)}
                              </time>
                            </div>
                            <p className="mt-1 text-xs leading-relaxed text-slate-600">
                              {step.detail}
                            </p>
                            {step.code_excerpt ? (
                              <pre className="mt-2 overflow-x-auto rounded-lg border border-slate-200 bg-slate-950 px-3 py-2 font-mono text-[11px] leading-relaxed text-slate-100">
                                <code>{step.code_excerpt}</code>
                              </pre>
                            ) : null}
                          </div>
                        </li>
                      );
                    })}
                  </ol>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
