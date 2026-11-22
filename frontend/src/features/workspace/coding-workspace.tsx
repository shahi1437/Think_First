"use client";

import {
  AlertCircle,
  ArrowLeft,
  Bug,
  CheckCircle2,
  Clock,
  Code2,
  History,
  Loader2,
  Lock,
  Play,
  RotateCcw,
  Save,
  Send,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { VerdictBadge } from "@/components/ui/verdict-badge";
import { MentorPanel } from "@/features/mentor/mentor-panel";
import { TransferVerificationPanel } from "@/features/verification/transfer-verification-panel";
import { CodeEditor } from "@/features/workspace/code-editor";
import {
  createSubmission,
  fetchSubmissionDetail,
  fetchTransferChallenge,
  saveWorkspaceRevision,
} from "@/lib/api-client";
import type {
  MentorSessionDetail,
  TransferChallengeSummary,
} from "@/types/mentor";
import type {
  RevisionResponse,
  StudentProblemDetail,
  SubmissionResponse,
  SubmissionSummaryItem,
} from "@/types/problems";

type MobileTab = "problem" | "editor" | "results" | "mentor" | "verify";
type BottomTab = "results" | "mentor" | "verify" | "submissions" | "revisions";

interface CodingWorkspaceProps {
  accessToken: string;
  problem: StudentProblemDetail;
  initialSubmissions: SubmissionSummaryItem[];
  initialRevisions: RevisionResponse[];
  initialTransferChallenge?: TransferChallengeSummary | null;
  preferredLanguageSlug?: string;
  initialBottomTab?: BottomTab;
  usePlainEditor?: boolean;
  onExecuteCode?: (payload: {
    problem_id: string;
    language_slug: string;
    submission_kind: "run" | "submit";
    source_code: string;
    prediction_text?: string;
    explanation_text?: string;
  }) => Promise<SubmissionResponse>;
  onSaveRevision?: (payload: {
    problem_version_id: string;
    language_slug: string;
    source_code: string;
    prediction_text?: string;
    explanation_text?: string;
    revision_type: "autosave" | "manual";
  }) => Promise<RevisionResponse>;
}

export function CodingWorkspace({
  accessToken,
  problem,
  initialSubmissions,
  initialRevisions,
  initialTransferChallenge = null,
  preferredLanguageSlug,
  initialBottomTab,
  usePlainEditor = false,
  onExecuteCode,
  onSaveRevision,
}: CodingWorkspaceProps) {
  const defaultVariant =
    problem.variants.find((v) => v.language_slug === preferredLanguageSlug) ??
    problem.variants[0];
  const [selectedLang, setSelectedLang] = useState(
    defaultVariant?.language_slug ?? "python",
  );

  const activeVariant = useMemo(
    () =>
      problem.variants.find((v) => v.language_slug === selectedLang) ??
      defaultVariant,
    [problem.variants, selectedLang, defaultVariant],
  );

  const initialStarter =
    problem.mode === "debugging" && activeVariant?.buggy_starter_code
      ? activeVariant.buggy_starter_code
      : (activeVariant?.starter_code ?? "");

  const latestRevisionForLang = useMemo(
    () => initialRevisions.find((r) => r.language_slug === selectedLang),
    [initialRevisions, selectedLang],
  );

  const [code, setCode] = useState<string>(
    latestRevisionForLang?.source_code ?? initialStarter,
  );
  const [predictionText, setPredictionText] = useState<string>(
    latestRevisionForLang?.prediction_text ?? "",
  );
  const [explanationText, setExplanationText] = useState<string>(
    latestRevisionForLang?.explanation_text ?? "",
  );

  const [mobileTab, setMobileTab] = useState<MobileTab>(
    initialBottomTab === "verify"
      ? "verify"
      : initialBottomTab === "mentor"
        ? "mentor"
        : "problem",
  );
  const [bottomTab, setBottomTab] = useState<BottomTab>(
    initialBottomTab ?? "results",
  );

  const [submissions, setSubmissions] =
    useState<SubmissionSummaryItem[]>(initialSubmissions);
  const [revisions, setRevisions] =
    useState<RevisionResponse[]>(initialRevisions);
  const [activeSubmission, setActiveSubmission] =
    useState<SubmissionResponse | null>(null);
  const [mentorSession, setMentorSession] =
    useState<MentorSessionDetail | null>(null);
  const [transferChallenge, setTransferChallenge] =
    useState<TransferChallengeSummary | null>(initialTransferChallenge);

  const [runningKind, setRunningKind] = useState<"run" | "submit" | null>(null);
  const [loadingSubId, setLoadingSubId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [autosaveState, setAutosaveState] = useState<
    "idle" | "dirty" | "saving" | "saved" | "error"
  >("idle");
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(
    latestRevisionForLang?.created_at ?? null,
  );

  const lastSavedCodeRef = useRef<string>(code);
  const isDebugging = problem.mode === "debugging";

  const persistRevision = useCallback(
    async (kind: "autosave" | "manual") => {
      if (!code.trim()) return;
      setAutosaveState("saving");
      try {
        const payload = {
          problem_version_id: problem.version_id,
          language_slug: selectedLang,
          source_code: code,
          prediction_text: predictionText.trim() || undefined,
          explanation_text: explanationText.trim() || undefined,
          revision_type: kind,
        };
        const saved = onSaveRevision
          ? await onSaveRevision(payload)
          : await saveWorkspaceRevision(accessToken, payload);
        lastSavedCodeRef.current = code;
        setRevisions((prev) => [saved, ...prev.slice(0, 19)]);
        setLastSavedAt(saved.created_at);
        setAutosaveState("saved");
      } catch {
        setAutosaveState("error");
      }
    },
    [
      accessToken,
      code,
      explanationText,
      onSaveRevision,
      predictionText,
      problem.version_id,
      selectedLang,
    ],
  );

  // Debounced autosave when code changes (never overwrites local edits)
  useEffect(() => {
    if (code === lastSavedCodeRef.current) return;
    setAutosaveState("dirty");
    const handle = window.setTimeout(() => {
      void persistRevision("autosave");
    }, 3500);
    return () => window.clearTimeout(handle);
  }, [code, persistRevision]);

  function handleLanguageSwitch(nextSlug: string) {
    setSelectedLang(nextSlug);
    const variant = problem.variants.find((v) => v.language_slug === nextSlug);
    const existingRev = revisions.find((r) => r.language_slug === nextSlug);
    const starter =
      problem.mode === "debugging" && variant?.buggy_starter_code
        ? variant.buggy_starter_code
        : (variant?.starter_code ?? "");
    const nextCode = existingRev?.source_code ?? starter;
    setCode(nextCode);
    lastSavedCodeRef.current = nextCode;
    setAutosaveState("idle");
  }

  function handleResetStarter() {
    setCode(initialStarter);
    setAutosaveState("dirty");
  }

  async function handleExecute(kind: "run" | "submit") {
    setErrorMessage(null);
    setRunningKind(kind);
    try {
      const payload = {
        problem_id: problem.problem_id,
        language_slug: selectedLang,
        submission_kind: kind,
        source_code: code,
        prediction_text: predictionText.trim() || undefined,
        explanation_text: explanationText.trim() || undefined,
      };
      const result = onExecuteCode
        ? await onExecuteCode(payload)
        : await createSubmission(accessToken, payload);

      setActiveSubmission(result);
      setSubmissions((prev) => [
        {
          id: result.id,
          problem_id: result.problem_id,
          problem_version_id: result.problem_version_id,
          language_slug: result.language_slug,
          submission_kind: result.submission_kind,
          status: result.status,
          verdict: result.verdict,
          passed_tests: result.passed_tests,
          total_tests: result.total_tests,
          runtime_ms: result.runtime_ms,
          memory_kb: result.memory_kb,
          execution_provider: result.execution_provider ?? "judge0",
          created_at: result.created_at,
        },
        ...prev,
      ]);
      lastSavedCodeRef.current = code;
      setAutosaveState("saved");
      setLastSavedAt(result.created_at);
      setBottomTab("results");
      setMobileTab("results");

      // Refresh linked independent transfer challenge unlock state after Submit Code passes
      if (result.submission_kind === "submit" && result.verdict === "accepted") {
        fetchTransferChallenge(accessToken, problem.problem_id)
          .then((nextChallenge) => setTransferChallenge(nextChallenge))
          .catch(() => undefined);
      }
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Execution request failed. Please try again.",
      );
      setBottomTab("results");
      setMobileTab("results");
    } finally {
      setRunningKind(null);
    }
  }

  async function handleInspectSubmission(submissionId: string) {
    setLoadingSubId(submissionId);
    setErrorMessage(null);
    try {
      const detail = await fetchSubmissionDetail(accessToken, submissionId);
      setActiveSubmission(detail);
      setBottomTab("results");
      setMobileTab("results");
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Could not load submission.",
      );
    } finally {
      setLoadingSubId(null);
    }
  }

  function handleRestoreRevision(rev: RevisionResponse) {
    setCode(rev.source_code);
    if (rev.prediction_text) setPredictionText(rev.prediction_text);
    if (rev.explanation_text) setExplanationText(rev.explanation_text);
    lastSavedCodeRef.current = rev.source_code;
    setAutosaveState("saved");
    setMobileTab("editor");
  }

  // Real evidence-driven debugging workflow steps
  const hasRun = submissions.some((s) => s.submission_kind === "run") ||
    activeSubmission !== null;
  const hasModifiedStarter = code.trim() !== initialStarter.trim();
  const hasAcceptedSubmit =
    activeSubmission?.submission_kind === "submit" &&
    activeSubmission.verdict === "accepted" ||
    submissions.some(
      (s) => s.submission_kind === "submit" && s.verdict === "accepted",
    );

  const debuggingSteps = [
    { label: "Understand", done: true },
    { label: "Predict", done: predictionText.trim().length >= 5 },
    { label: "Run", done: hasRun },
    { label: "Investigate", done: hasRun },
    { label: "Explain", done: explanationText.trim().length >= 10 },
    { label: "Fix", done: hasModifiedStarter },
    { label: "Verify", done: hasAcceptedSubmit },
  ];

  return (
    <div className="tf-animate-enter space-y-4 overflow-x-hidden">
      {/* Workspace Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-3.5 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/student/problems"
            className="tf-btn-press inline-flex min-h-[40px] items-center gap-1.5 rounded-xl border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            <span>Problems</span>
          </Link>

          <h1 className="text-lg font-bold text-slate-900 sm:text-xl">
            {problem.title}
          </h1>

          <Badge variant={isDebugging ? "indigo" : "teal"}>
            {isDebugging ? (
              <Bug className="h-3.5 w-3.5" aria-hidden="true" />
            ) : (
              <Code2 className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            <span className="capitalize">{problem.mode} Mode</span>
          </Badge>
          <Badge variant="neutral">
            <span className="capitalize">{problem.difficulty}</span>
          </Badge>
        </div>

        <div className="flex items-center gap-2 text-sm text-slate-600">
          <Clock className="h-4 w-4" aria-hidden="true" />
          <span>
            Limit: {problem.time_limit_ms / 1000}s ·{" "}
            {Math.round(problem.memory_limit_kb / 1024)} MB
          </span>
        </div>
      </div>

      {/* Post-Accepted Next Recommended Step Callout (No Dead End) */}
      {hasAcceptedSubmit ? (
        <div
          role="status"
          className="tf-celebrate-pop flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-emerald-200 bg-emerald-50/80 px-5 py-3.5 text-sm text-emerald-950"
        >
          <div className="flex items-center gap-2.5">
            <CheckCircle2
              className="h-5 w-5 shrink-0 text-emerald-700"
              aria-hidden="true"
            />
            <div>
              <p className="font-bold">
                Accepted Solution Verified in Isolated Sandbox!
              </p>
              <p className="text-emerald-900">
                {transferChallenge?.unlocked &&
                transferChallenge.latest_attempt?.outcome !==
                  "verified_independent"
                  ? "Your Independent Transfer Verification challenge is now unlocked — solve it with zero hints to earn Transferred."
                  : "Your progress and Skill Graph have been updated. Ready for your next learning step?"}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {transferChallenge?.unlocked &&
            transferChallenge.latest_attempt?.outcome !==
              "verified_independent" ? (
              <button
                type="button"
                onClick={() => {
                  setBottomTab("verify");
                  setMobileTab("verify");
                }}
                className="tf-btn-press inline-flex min-h-[40px] items-center gap-1.5 rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-600"
              >
                <span>Open Independent Transfer Check →</span>
              </button>
            ) : null}
            <Link
              href="/student"
              className="tf-btn-press inline-flex min-h-[40px] items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
            >
              <span>Continue Learning →</span>
            </Link>
          </div>
        </div>
      ) : null}

      {/* Debugging 7-step Workflow Strip */}
      {isDebugging ? (
        <nav
          aria-label="Debugging workflow steps"
          className="flex flex-wrap items-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50/60 px-4 py-2.5"
        >
          {debuggingSteps.map((step, idx) => (
            <div key={step.label} className="flex items-center gap-1.5 text-xs">
              <span
                className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-semibold ${step.done
                  ? "bg-indigo-600 text-white"
                  : "border border-indigo-300 bg-white text-indigo-700"
                  }`}
              >
                {idx + 1}
              </span>
              <span
                className={
                  step.done
                    ? "font-semibold text-indigo-950"
                    : "text-indigo-800/80"
                }
              >
                {step.label}
              </span>
              {idx < debuggingSteps.length - 1 ? (
                <span className="mx-1 text-indigo-300" aria-hidden="true">
                  →
                </span>
              ) : null}
            </div>
          ))}
        </nav>
      ) : null}

      {/* Mobile / Tablet Accessible Tab Bar */}
      <div
        role="tablist"
        aria-label="Workspace panels"
        className="grid grid-cols-5 gap-1 rounded-xl border border-slate-200 bg-white p-1 lg:hidden"
      >
        {(
          [
            ["problem", "Problem"],
            ["editor", "Editor"],
            ["results", "Results"],
            ["mentor", "Mentor"],
            ["verify", "Transfer"],
          ] as const
        ).map(([tabKey, label]) => (
          <button
            key={tabKey}
            type="button"
            role="tab"
            aria-selected={mobileTab === tabKey}
            onClick={() => {
              setMobileTab(tabKey);
              if (tabKey === "results") setBottomTab("results");
              if (tabKey === "mentor") setBottomTab("mentor");
              if (tabKey === "verify") setBottomTab("verify");
            }}
            className={`truncate rounded-lg px-1.5 py-2 text-[11px] font-semibold transition sm:text-xs ${mobileTab === tabKey
              ? "bg-indigo-600 text-white"
              : "text-slate-600 hover:bg-slate-100"
              }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Main Split Layout */}
      <div className="grid gap-4 lg:grid-cols-12">
        {/* LEFT PANE: Problem Description + Debugging Prompts */}
        <section
          aria-label="Problem specification"
          className={`min-w-0 space-y-5 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5 lg:col-span-5 ${mobileTab === "problem" ? "block" : "hidden lg:block"
            }`}
        >
          <div className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
              Problem Statement
            </h2>
            <div className="whitespace-pre-line text-sm leading-relaxed text-slate-800">
              {problem.statement_md}
            </div>
          </div>

          {problem.learning_objectives.length > 0 ? (
            <div className="space-y-2 border-t border-slate-100 pt-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Learning Objectives
              </h3>
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                {problem.learning_objectives.map((obj) => (
                  <li key={obj}>{obj}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {problem.examples.length > 0 ? (
            <div className="space-y-3 border-t border-slate-100 pt-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Examples
              </h3>
              {problem.examples.map((ex, idx) => (
                <div
                  key={idx}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs"
                >
                  <div className="grid gap-2 sm:grid-cols-2">
                    <div>
                      <p className="font-semibold text-slate-600">Input</p>
                      <pre className="mt-1 overflow-x-auto rounded bg-white p-2 font-mono text-slate-900">
                        {ex.input}
                      </pre>
                    </div>
                    <div>
                      <p className="font-semibold text-slate-600">Output</p>
                      <pre className="mt-1 overflow-x-auto rounded bg-white p-2 font-mono text-slate-900">
                        {ex.output}
                      </pre>
                    </div>
                  </div>
                  {ex.explanation ? (
                    <p className="mt-2 text-slate-600">{ex.explanation}</p>
                  ) : null}
                </div>
              ))}
            </div>
          ) : null}

          <div className="border-t border-slate-100 pt-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Test Suite Coverage
            </h3>
            <p className="mt-1 text-xs text-slate-600">
              <strong>{problem.public_test_cases.length}</strong> public tests
              run on <em>Run Code</em>;{" "}
              <strong>
                {problem.public_test_cases.length + problem.hidden_test_count}
              </strong>{" "}
              total tests ({problem.hidden_test_count} hidden) run on{" "}
              <em>Submit Code</em>.
            </p>
          </div>

          {/* Debugging Mode Guided Reflection Inputs */}
          {isDebugging ? (
            <div className="space-y-4 rounded-xl border border-indigo-200 bg-indigo-50/40 p-4">
              <div>
                <h3 className="text-sm font-semibold text-indigo-950">
                  Step 2 — Predict Output Before Running
                </h3>
                {activeVariant?.debugging_prompt ? (
                  <p className="mt-1 text-xs text-indigo-900">
                    {activeVariant.debugging_prompt}
                  </p>
                ) : null}
                <textarea
                  aria-label="Output prediction"
                  rows={2}
                  value={predictionText}
                  onChange={(e) => setPredictionText(e.target.value)}
                  placeholder="Write what you expect the buggy code to output and why..."
                  className="mt-2 w-full rounded-lg border border-indigo-200 bg-white px-3 py-2 text-xs text-slate-900 focus:border-indigo-600 focus:outline-none"
                />
              </div>

              <div>
                <h3 className="text-sm font-semibold text-indigo-950">
                  Step 5 — Explain the Root Cause
                </h3>
                <textarea
                  aria-label="Bug explanation"
                  rows={3}
                  value={explanationText}
                  onChange={(e) => setExplanationText(e.target.value)}
                  placeholder="After running and investigating the mismatch, explain why the bug happened and how your fix resolves it..."
                  className="mt-2 w-full rounded-lg border border-indigo-200 bg-white px-3 py-2 text-xs text-slate-900 focus:border-indigo-600 focus:outline-none"
                />
              </div>

              <p className="text-[11px] text-slate-600">
                Your prediction, explanation, and Judge0 execution results are
                saved as structured learning evidence for Phase 4 Socratic AI
                mentoring.
              </p>
            </div>
          ) : null}
        </section>

        {/* RIGHT PANE: Editor + Execution Results & History */}
        <div className="min-w-0 space-y-4 lg:col-span-7">
          {/* Code Editor Card */}
          <section
            aria-label="Code editor workspace"
            className={`overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm ${mobileTab === "editor" ? "block" : "hidden lg:block"
              }`}
          >
            {/* Editor Toolbar */}
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-slate-900 px-4 py-2.5 text-white">
              <div className="flex items-center gap-2">
                <label htmlFor="workspace-lang-select" className="sr-only">
                  Programming language
                </label>
                <select
                  id="workspace-lang-select"
                  value={selectedLang}
                  onChange={(e) => handleLanguageSwitch(e.target.value)}
                  className="rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs font-medium text-white focus:border-teal-400 focus:outline-none"
                >
                  {problem.variants.map((v) => (
                    <option key={v.language_slug} value={v.language_slug}>
                      {v.display_name}
                    </option>
                  ))}
                </select>

                <button
                  type="button"
                  onClick={handleResetStarter}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-700 px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-white"
                  title="Reset editor to starter code"
                >
                  <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>Reset</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    void persistRevision("manual");
                  }}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-700 px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-white"
                >
                  <Save className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>Save</span>
                </button>
              </div>

              <div className="flex items-center gap-2">
                <span
                  aria-live="polite"
                  className="text-[11px] text-slate-400"
                >
                  {autosaveState === "saving"
                    ? "Saving..."
                    : autosaveState === "dirty"
                      ? "Unsaved edits"
                      : autosaveState === "error"
                        ? "Autosave failed"
                        : lastSavedAt
                          ? "Saved"
                          : "Ready"}
                </span>

                <button
                  type="button"
                  disabled={runningKind !== null || !code.trim()}
                  onClick={() => {
                    void handleExecute("run");
                  }}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-teal-500/40 bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-teal-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {runningKind === "run" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Play className="h-3.5 w-3.5" aria-hidden="true" />
                  )}
                  <span>
                    {runningKind === "run" ? "Running..." : "Run Code"}
                  </span>
                </button>

                <button
                  type="button"
                  disabled={runningKind !== null || !code.trim()}
                  onClick={() => {
                    void handleExecute("submit");
                  }}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {runningKind === "submit" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Send className="h-3.5 w-3.5" aria-hidden="true" />
                  )}
                  <span>
                    {runningKind === "submit" ? "Evaluating..." : "Submit Code"}
                  </span>
                </button>
              </div>
            </div>

            <CodeEditor
              language={activeVariant?.monaco_language ?? "python"}
              value={code}
              onChange={setCode}
              usePlainTextarea={usePlainEditor}
            />
          </section>

          {/* Bottom Panel: Results / AI Mentor / Transfer Verify / Submissions / Revisions */}
          <section
            aria-label="Execution results, AI Mentor, and verification"
            className={`rounded-xl border border-slate-200 bg-white shadow-sm ${mobileTab === "results" ||
              mobileTab === "mentor" ||
              mobileTab === "verify"
              ? "block"
              : "hidden lg:block"
              }`}
          >
            <div className="flex flex-wrap items-center gap-1 border-b border-slate-200 px-3 pt-2 sm:px-4">
              {(
                [
                  ["results", "Execution Results"],
                  ["mentor", "AI Mentor"],
                  [
                    "verify",
                    transferChallenge?.unlocked
                      ? "Transfer Check (Unlocked)"
                      : "Transfer Check",
                  ],
                  ["submissions", `Submissions (${submissions.length})`],
                  ["revisions", `Revisions (${revisions.length})`],
                ] as const
              ).map(([tabKey, label]) => (
                <button
                  key={tabKey}
                  type="button"
                  onClick={() => setBottomTab(tabKey)}
                  className={`border-b-2 px-3 py-2 text-xs font-semibold transition ${bottomTab === tabKey
                    ? "border-indigo-600 text-indigo-700"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                    }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="p-4">
              {errorMessage ? (
                <div
                  role="alert"
                  className="mb-4 flex items-start gap-2.5 rounded-lg border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-900"
                >
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
                  <span>{errorMessage}</span>
                </div>
              ) : null}

              {bottomTab === "results" ? (
                runningKind ? (
                  <div className="flex items-center gap-3 rounded-lg bg-slate-50 p-6 text-sm text-slate-700">
                    <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
                    <span>
                      Executing inside isolated Judge0 sandbox (
                      {runningKind === "run"
                        ? "public tests"
                        : "public + hidden tests"}
                      )...
                    </span>
                  </div>
                ) : activeSubmission ? (
                  <div className="space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3.5">
                      <div className="flex flex-wrap items-center gap-3">
                        <VerdictBadge verdict={activeSubmission.verdict} />
                        <span className="text-sm font-semibold text-slate-900">
                          {activeSubmission.passed_tests} /{" "}
                          {activeSubmission.total_tests} tests passed
                        </span>
                        <Badge variant="neutral">
                          <span className="uppercase">
                            {activeSubmission.submission_kind}
                          </span>
                        </Badge>
                        {activeSubmission.execution_provider ? (
                          <Badge
                            variant={
                              activeSubmission.execution_provider === "piston"
                                ? "indigo"
                                : "neutral"
                            }
                          >
                            {activeSubmission.execution_provider === "piston"
                              ? "Piston Fallback"
                              : "Judge0 CE"}
                          </Badge>
                        ) : null}
                      </div>
                      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                        <span>
                          {activeSubmission.runtime_ms != null
                            ? `${activeSubmission.runtime_ms} ms`
                            : "—"}
                          {" · "}
                          {activeSubmission.memory_kb != null
                            ? `${activeSubmission.memory_kb} KB`
                            : "—"}
                        </span>
                        {activeSubmission.verdict !== "accepted" ? (
                          <button
                            type="button"
                            onClick={() => {
                              setBottomTab("mentor");
                              setMobileTab("mentor");
                            }}
                            className="rounded-md bg-indigo-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-indigo-500"
                          >
                            Ask Socratic AI Mentor →
                          </button>
                        ) : transferChallenge?.unlocked ? (
                          <button
                            type="button"
                            onClick={() => {
                              setBottomTab("verify");
                              setMobileTab("verify");
                            }}
                            className="rounded-md bg-teal-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-teal-500"
                          >
                            Open Transfer Check →
                          </button>
                        ) : null}
                      </div>
                    </div>

                    <div className="space-y-3">
                      {activeSubmission.results.map((res) => (
                        <div
                          key={`${res.ordinal}-${res.name}`}
                          className="rounded-lg border border-slate-200 p-3 text-xs"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-2 font-semibold text-slate-800">
                              {res.is_hidden ? (
                                <Lock
                                  className="h-3.5 w-3.5 text-slate-400"
                                  aria-hidden="true"
                                />
                              ) : null}
                              <span>{res.name}</span>
                            </div>
                            <VerdictBadge verdict={res.verdict} />
                          </div>

                          {res.is_hidden ? (
                            <p className="mt-2 text-slate-500">
                              Hidden test input and expected output remain
                              private.
                            </p>
                          ) : (
                            <div className="mt-2.5 grid gap-2 sm:grid-cols-3">
                              <div>
                                <p className="font-medium text-slate-500">
                                  Input
                                </p>
                                <pre className="mt-1 overflow-x-auto rounded bg-slate-50 p-2 font-mono text-slate-900">
                                  {res.input_data ?? ""}
                                </pre>
                              </div>
                              <div>
                                <p className="font-medium text-slate-500">
                                  Expected
                                </p>
                                <pre className="mt-1 overflow-x-auto rounded bg-slate-50 p-2 font-mono text-slate-900">
                                  {res.expected_output ?? ""}
                                </pre>
                              </div>
                              <div>
                                <p className="font-medium text-slate-500">
                                  Actual Output
                                </p>
                                <pre className="mt-1 overflow-x-auto rounded bg-slate-50 p-2 font-mono text-slate-900">
                                  {res.stdout ?? "(empty)"}
                                </pre>
                              </div>
                            </div>
                          )}

                          {res.stderr ? (
                            <div className="mt-2">
                              <p className="font-medium text-rose-700">
                                Runtime Error (stderr)
                              </p>
                              <pre className="mt-1 overflow-x-auto rounded bg-rose-50 p-2 font-mono text-rose-900">
                                {res.stderr}
                              </pre>
                            </div>
                          ) : null}

                          {res.compile_output ? (
                            <div className="mt-2">
                              <p className="font-medium text-amber-800">
                                Compiler Output
                              </p>
                              <pre className="mt-1 overflow-x-auto rounded bg-amber-50 p-2 font-mono text-amber-950">
                                {res.compile_output}
                              </pre>
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-600">
                    Click <strong>Run Code</strong> to execute public tests or{" "}
                    <strong>Submit Code</strong> to evaluate against all public
                    and hidden tests in Judge0.
                  </div>
                )
              ) : bottomTab === "mentor" ? (
                <MentorPanel
                  accessToken={accessToken}
                  problemId={problem.problem_id}
                  latestSubmissionId={
                    activeSubmission?.id ?? submissions[0]?.id ?? null
                  }
                  latestVerdict={
                    activeSubmission?.verdict ?? submissions[0]?.verdict ?? null
                  }
                  session={mentorSession}
                  onSessionChange={setMentorSession}
                />
              ) : bottomTab === "verify" ? (
                <TransferVerificationPanel
                  accessToken={accessToken}
                  challenge={transferChallenge}
                  activeLanguageSlug={selectedLang}
                  latestAcceptedSubmissionId={
                    submissions.find(
                      (s) =>
                        s.submission_kind === "submit" &&
                        s.verdict === "accepted",
                    )?.id ?? null
                  }
                  usePlainEditor={usePlainEditor}
                  onRefreshChallenge={async () => {
                    try {
                      const refreshed = await fetchTransferChallenge(
                        accessToken,
                        problem.problem_id,
                      );
                      setTransferChallenge(refreshed);
                    } catch {
                      // ignore transient refresh failure
                    }
                  }}
                />
              ) : bottomTab === "submissions" ? (
                submissions.length === 0 ? (
                  <p className="py-6 text-center text-sm text-slate-500">
                    No submissions yet for this problem.
                  </p>
                ) : (
                  <ul className="divide-y divide-slate-100">
                    {submissions.map((sub) => (
                      <li
                        key={sub.id}
                        className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-xs"
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <VerdictBadge verdict={sub.verdict} />
                          <span className="font-medium text-slate-800">
                            {sub.passed_tests}/{sub.total_tests} passed
                          </span>
                          <Badge variant="neutral">
                            <span className="uppercase">
                              {sub.submission_kind}
                            </span>
                          </Badge>
                          <span className="text-slate-400">
                            {new Date(sub.created_at).toLocaleString()}
                          </span>
                        </div>
                        <button
                          type="button"
                          disabled={loadingSubId === sub.id}
                          onClick={() => {
                            void handleInspectSubmission(sub.id);
                          }}
                          className="font-medium text-indigo-700 hover:underline disabled:opacity-50"
                        >
                          {loadingSubId === sub.id
                            ? "Loading..."
                            : "Inspect results"}
                        </button>
                      </li>
                    ))}
                  </ul>
                )
              ) : revisions.length === 0 ? (
                <p className="py-6 text-center text-sm text-slate-500">
                  Autosave and manual revisions will appear here as you edit.
                </p>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {revisions.map((rev) => (
                    <li
                      key={rev.id}
                      className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <History
                          className="h-3.5 w-3.5 text-slate-400"
                          aria-hidden="true"
                        />
                        <Badge variant="neutral">
                          <span className="capitalize">
                            {rev.revision_type}
                          </span>
                        </Badge>
                        <span className="font-mono text-slate-600">
                          {rev.language_slug}
                        </span>
                        <span className="text-slate-400">
                          {new Date(rev.created_at).toLocaleString()}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRestoreRevision(rev)}
                        className="inline-flex items-center gap-1 font-medium text-indigo-700 hover:underline"
                      >
                        <CheckCircle2
                          className="h-3.5 w-3.5"
                          aria-hidden="true"
                        />
                        <span>Restore snapshot</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
