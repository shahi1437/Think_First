"use client";

import {
  AlertCircle,
  ArrowRight,
  Award,
  CheckCircle2,
  ClipboardCheck,
  Code2,
  History,
  Loader2,
  Play,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { CodeEditor } from "@/features/workspace/code-editor";
import {
  startOrResumeDiagnosticSession,
  submitDiagnosticAnswer,
} from "@/lib/api-client";
import type { DiagnosticSessionView } from "@/types/learning";

interface DiagnosticWorkspaceProps {
  accessToken: string;
  initialHistory: DiagnosticSessionView[];
  initialLanguage?: "en" | "bn";
  usePlainEditor?: boolean;
  onStartSession?: (lang: "en" | "bn") => Promise<DiagnosticSessionView>;
  onSubmitAnswer?: (
    sessionId: string,
    payload: {
      question_id: string;
      selected_option_id?: string;
      source_code?: string;
    },
  ) => Promise<DiagnosticSessionView>;
}

const DOMAIN_LABELS: Record<string, string> = {
  variables: "Variables & Initialization",
  syntax_runtime_debugging: "Syntax & Runtime Debugging",
  conditions: "Conditions & Branching",
  loop_boundaries: "Loop Boundaries",
  arrays_lists: "Arrays & Lists",
  indexing: "0-Based Indexing",
  functions: "Functions & Returns",
  mixed_logic: "Mixed Problem-Solving Logic",
};

export function DiagnosticWorkspace({
  accessToken,
  initialHistory,
  initialLanguage = "en",
  usePlainEditor = false,
  onStartSession,
  onSubmitAnswer,
}: DiagnosticWorkspaceProps) {
  const activeInProgress =
    initialHistory.find((s) => s.status === "in_progress") ?? null;
  const [session, setSession] = useState<DiagnosticSessionView | null>(
    activeInProgress,
  );
  const [history, setHistory] =
    useState<DiagnosticSessionView[]>(initialHistory);
  const [lang, setLang] = useState<"en" | "bn">(initialLanguage);
  const [selectedOption, setSelectedOption] = useState<string>("");
  const [codeAnswer, setCodeAnswer] = useState<string>(
    activeInProgress?.current_question?.starter_code ?? "",
  );
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isBn = lang === "bn";

  async function handleStartDiagnostic() {
    setErrorMsg(null);
    setLoading(true);
    try {
      const started = onStartSession
        ? await onStartSession(lang)
        : await startOrResumeDiagnosticSession(accessToken, lang);
      setSession(started);
      setSelectedOption("");
      setCodeAnswer(started.current_question?.starter_code ?? "");
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Could not start diagnostic session.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit() {
    if (!session || !session.current_question) return;
    const q = session.current_question;
    setErrorMsg(null);
    setLoading(true);
    try {
      const payload =
        q.question_type === "mcq"
          ? { question_id: q.id, selected_option_id: selectedOption }
          : { question_id: q.id, source_code: codeAnswer };

      const updated = onSubmitAnswer
        ? await onSubmitAnswer(session.id, payload)
        : await submitDiagnosticAnswer(accessToken, session.id, payload);

      setSession(updated);
      setSelectedOption("");
      setCodeAnswer(updated.current_question?.starter_code ?? "");
      if (updated.status === "completed") {
        setHistory((prev) => [
          updated,
          ...prev.filter((s) => s.id !== updated.id),
        ]);
      }
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Could not submit diagnostic answer.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6" lang={lang}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <ClipboardCheck
              className="h-5 w-5 text-indigo-600"
              aria-hidden="true"
            />
            <h1 className="text-xl font-bold text-slate-900">
              {isBn
                ? "৮-ডোমেইন অ্যাডাপ্টিভ ডায়াগনস্টিক অ্যাসেসমেন্ট"
                : "8-Domain Adaptive Diagnostic Assessment"}
            </h1>
          </div>
          <p className="mt-1 text-xs text-slate-600">
            {isBn
              ? "অ্যাডাপ্টিভ ফলো-আপ প্রশ্ন এবং আসল Judge0 কোড এক্সিকিউশন দিয়ে তোমার প্রকৃত দক্ষতা যাচাই করো।"
              : "Evaluates 8 Python domains with adaptive follow-up questions and real Judge0 execution checks—no fabricated marks or IQ scores."}
          </p>
        </div>

        <div
          role="group"
          aria-label="Diagnostic language"
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

      {errorMsg ? (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-900"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
          <span>{errorMsg}</span>
        </div>
      ) : null}

      {/* Last Feedback Banner */}
      {session?.last_feedback ? (
        <div
          role="status"
          className={`rounded-xl border p-4 text-xs ${
            session.last_feedback.is_correct
              ? "border-emerald-200 bg-emerald-50/70 text-emerald-950"
              : "border-amber-200 bg-amber-50/70 text-amber-950"
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-2 font-bold">
            <span>
              {session.last_feedback.is_correct
                ? "Previous check: Correct"
                : "Previous check: Gap Observed"}
            </span>
            {session.last_feedback.question_type === "code_execution" ? (
              <Badge variant="teal">
                Judge0: {session.last_feedback.passed_tests}/
                {session.last_feedback.total_tests} passed (
                {session.last_feedback.execution_verdict})
              </Badge>
            ) : null}
          </div>
          <p className="mt-1">
            {isBn
              ? session.last_feedback.feedback_bn
              : session.last_feedback.feedback_en}
          </p>
          {session.last_feedback.adaptive_action ? (
            <p className="mt-1.5 flex items-center gap-1.5 font-semibold text-indigo-800">
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              <span>{session.last_feedback.adaptive_action}</span>
            </p>
          ) : null}
        </div>
      ) : null}

      {/* Start Card when no active session */}
      {!session ? (
        <div className="space-y-4 rounded-2xl border border-indigo-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-bold text-slate-900">
            Ready to discover your actual Python baseline?
          </h2>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(DOMAIN_LABELS).map(([slug, label]) => (
              <div
                key={slug}
                className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-700"
              >
                {label}
              </div>
            ))}
          </div>
          <button
            type="button"
            disabled={loading}
            onClick={() => {
              void handleStartDiagnostic();
            }}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-60"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" aria-hidden="true" />
            )}
            <span>
              {isBn
                ? "ডায়াগনস্টিক অ্যাসেসমেন্ট শুরু করো"
                : "Start Adaptive Diagnostic"}
            </span>
          </button>
        </div>
      ) : session.status === "in_progress" && session.current_question ? (
        /* Active Question Card */
        <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="indigo">
                {DOMAIN_LABELS[session.current_question.domain_slug] ??
                  session.current_question.domain_slug}
              </Badge>
              <Badge variant="neutral">
                <span className="capitalize">
                  {session.current_question.difficulty}
                </span>
              </Badge>
              {session.current_question.question_type === "code_execution" ? (
                <Badge variant="teal">
                  <Code2 className="h-3 w-3" aria-hidden="true" />
                  <span>Real Judge0 Execution Check</span>
                </Badge>
              ) : null}
            </div>
            <span className="text-xs font-medium text-slate-500">
              Answered {session.answered_count} · Remaining{" "}
              {session.remaining_count}
              {session.adaptive_followups_added > 0
                ? ` · +${session.adaptive_followups_added} adaptive`
                : ""}
            </span>
          </div>

          <h2 className="text-base font-bold leading-relaxed text-slate-900">
            {isBn
              ? session.current_question.prompt_bn
              : session.current_question.prompt_en}
          </h2>

          {session.current_question.code_snippet ? (
            <pre className="overflow-x-auto rounded-xl bg-slate-900 p-4 font-mono text-xs leading-relaxed text-slate-100">
              {session.current_question.code_snippet}
            </pre>
          ) : null}

          {session.current_question.question_type === "mcq" ? (
            <fieldset className="space-y-2.5">
              <legend className="sr-only">Diagnostic options</legend>
              {session.current_question.options.map((opt) => (
                <label
                  key={opt.id}
                  className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3.5 text-sm transition ${
                    selectedOption === opt.id
                      ? "border-indigo-600 bg-indigo-50/60"
                      : "border-slate-200 bg-white hover:bg-slate-50"
                  }`}
                >
                  <input
                    type="radio"
                    name="diag-option"
                    value={opt.id}
                    checked={selectedOption === opt.id}
                    onChange={() => setSelectedOption(opt.id)}
                    className="mt-1"
                  />
                  <span className="text-slate-800">
                    {isBn ? opt.text_bn : opt.text_en}
                  </span>
                </label>
              ))}
            </fieldset>
          ) : (
            <div className="overflow-hidden rounded-xl border border-slate-200">
              <div className="bg-slate-900 px-3.5 py-2 text-xs font-semibold text-slate-200">
                Python 3 Execution Editor (Evaluated on Judge0 CE)
              </div>
              <CodeEditor
                language="python"
                value={codeAnswer}
                onChange={setCodeAnswer}
                usePlainTextarea={usePlainEditor}
              />
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              type="button"
              disabled={
                loading ||
                (session.current_question.question_type === "mcq"
                  ? !selectedOption
                  : !codeAnswer.trim())
              }
              onClick={() => {
                void handleSubmit();
              }}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              )}
              <span>
                {loading
                  ? session.current_question.question_type === "code_execution"
                    ? "Running on Judge0..."
                    : "Evaluating..."
                  : "Submit Answer"}
              </span>
            </button>
          </div>
        </div>
      ) : (
        /* Completed Diagnostic Evidence Report */
        <div className="space-y-5 rounded-2xl border border-emerald-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <Award className="h-6 w-6 text-emerald-600" aria-hidden="true" />
              <div>
                <h2 className="text-lg font-bold text-slate-900">
                  Diagnostic Completed — Evidence-Based Track Placement
                </h2>
                <p className="text-xs text-slate-600">
                  Answered {session.answered_count} checks (including{" "}
                  {session.adaptive_followups_added} adaptive follow-ups)
                </p>
              </div>
            </div>
            {session.recommended_track_slug ? (
              <Badge variant="emerald">
                <span className="capitalize">
                  Recommended Track:{" "}
                  {session.recommended_track_slug.replaceAll("_", " ")}
                </span>
              </Badge>
            ) : null}
          </div>

          {session.recommendation_rationale ? (
            <p className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 text-sm text-emerald-950">
              {session.recommendation_rationale}
            </p>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2">
            {session.domain_evidence.map((ev) => (
              <div
                key={ev.domain_slug}
                className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 text-xs"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-slate-900">
                    {DOMAIN_LABELS[ev.domain_slug] ?? ev.domain_slug}
                  </span>
                  <Badge
                    variant={
                      ev.evidence_status === "demonstrated_strong"
                        ? "emerald"
                        : ev.evidence_status === "demonstrated_basic"
                          ? "teal"
                          : ev.evidence_status === "gap_detected"
                            ? "rose"
                            : "amber"
                    }
                  >
                    <span className="capitalize">
                      {ev.evidence_status.replaceAll("_", " ")}
                    </span>
                  </Badge>
                </div>
                <p className="mt-1 text-slate-600">
                  Observed: <strong>{ev.observed_correct}</strong> /{" "}
                  <strong>{ev.observed_attempts}</strong>
                  {ev.execution_verified ? " · Judge0 Execution Verified" : ""}
                </p>
                <p className="mt-1 text-slate-700">
                  {isBn ? ev.note_bn : ev.note_en}
                </p>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-3 pt-2">
            <Link
              href="/student"
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500"
            >
              <span>View Updated Skill Graph &amp; Recommendations</span>
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Link>
            <Link
              href="/student/lessons"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50"
            >
              <span>Start Beginner Python Lessons</span>
            </Link>
          </div>
        </div>
      )}

      {/* Assessment History */}
      {history.length > 0 ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900">
            <History className="h-4 w-4 text-slate-500" aria-hidden="true" />
            <span>Diagnostic Assessment History</span>
          </div>
          <ul className="divide-y divide-slate-100 text-xs">
            {history.map((item) => (
              <li
                key={item.id}
                className="flex flex-wrap items-center justify-between gap-2 py-2.5"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <CheckCircle2
                    className={`h-3.5 w-3.5 ${
                      item.status === "completed"
                        ? "text-emerald-600"
                        : "text-amber-600"
                    }`}
                  />
                  <Badge variant="neutral">
                    <span className="capitalize">
                      {item.status.replaceAll("_", " ")}
                    </span>
                  </Badge>
                  <span className="font-medium text-slate-800">
                    {item.answered_count} checks answered
                  </span>
                  {item.recommended_track_slug ? (
                    <Badge variant="indigo">
                      Track: {item.recommended_track_slug.replaceAll("_", " ")}
                    </Badge>
                  ) : null}
                </div>
                <span className="text-slate-400">
                  {new Date(item.started_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
