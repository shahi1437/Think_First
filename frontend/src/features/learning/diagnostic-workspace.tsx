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
import {
  getLanguageDisplayName,
  getMonacoLanguageForSlug,
} from "@/lib/languages";
import { formatUtcDateTime } from "@/lib/format-date";
import type { DiagnosticSessionView } from "@/types/learning";
import type { AssessmentMode, DiagnosticSessionView } from "@/types/learning";

interface DiagnosticWorkspaceProps {
  accessToken: string;
  initialHistory: DiagnosticSessionView[];
  activeLanguageSlug?: string;
  initialLanguage?: "en" | "bn";
  recommendedMode?: AssessmentMode;
  fromOnboarding?: boolean;
  usePlainEditor?: boolean;
  onStartSession?: (lang: "en" | "bn") => Promise<DiagnosticSessionView>;
  onStartSession?: (
    lang: "en" | "bn",
    mode?: AssessmentMode,
  ) => Promise<DiagnosticSessionView>;
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
  activeLanguageSlug = "python",
  initialLanguage = "en",
  recommendedMode = "full",
  fromOnboarding = false,
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
  const [startingMode, setStartingMode] = useState<AssessmentMode | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isBn = lang === "bn";
  const langLabel = getLanguageDisplayName(
    session?.language_slug || activeLanguageSlug,
  );
  const questionLangSlug =
    session?.current_question?.language_slug || activeLanguageSlug;
  const questionLangLabel = getLanguageDisplayName(questionLangSlug);
  const questionMonacoLang = getMonacoLanguageForSlug(questionLangSlug);

  async function handleStartDiagnostic() {
    async function handleStartDiagnostic(mode: AssessmentMode = "full") {
      setErrorMsg(null);
      setLoading(true);
      setStartingMode(mode);
      try {
        const started = onStartSession
          ? await onStartSession(lang)
          : await startOrResumeDiagnosticSession(accessToken, lang);
        ?await onStartSession(lang, mode)
        : await startOrResumeDiagnosticSession(
            accessToken,
            lang,
            undefined,
            mode,
          );
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
        setStartingMode(null);
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
          <div className="tf-animate-enter flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-2.5">
                  <ClipboardCheck
                    className="h-5 w-5 text-indigo-600"
                    className="h-6 w-6 text-indigo-600"
                    aria-hidden="true"
                  />
                  <h1 className="text-xl font-bold text-slate-900">
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
                      {isBn
                        ? "৮-ডোমেইন অ্যাডাপ্টিভ ডায়াগনস্টিক অ্যাসেসমেন্ট"
                        : "8-Domain Adaptive Diagnostic Assessment"}
                      ? `${langLabel} অ্যাডাপ্টিভ অ্যাসেসমেন্ট`
                      : `${langLabel} Adaptive Entry Assessment`}
                    </h1>
                </div>
                <p className="mt-1 text-xs text-slate-600">
                  <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
                    {isBn
                      ? `অ্যাডাপ্টিভ ফলো-আপ প্রশ্ন এবং আসল স্যান্ডবক্স এক্সিকিউশন দিয়ে তোমার ${langLabel} দক্ষতা যাচাই করো।`
                      : `Evaluates 8 ${langLabel} domains with adaptive follow-up questions and real sandbox execution checks—no fabricated marks or IQ scores.`}
                    ? `নতুনদের জন্য সংক্ষিপ্ত ৪-ডোমেইন প্রস্তুতি যাচাই অথবা অভিজ্ঞদের জন্য পূর্ণ ৮-ডোমেইন অ্যাডাপ্টিভ ডায়াগনস্টিক—কোনো অনুমানকৃত নম্বর নয়, সম্পূর্ণ বাস্তব প্রমাণে ট্র্যাক নির্ধারণ।`
              : `Choose the 4-domain Short Readiness Check for beginners or the Full 8-Domain Adaptive Diagnostic with real sandbox execution checks—zero fabricated marks or IQ scores.`}
                  </p>
              </div>

              <div
                role="group"
                aria-label="Diagnostic language"
                className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-xs"
                className="inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1 text-sm"
              >
                <button
                  type="button"
                  onClick={() => setLang("en")}
                  aria-pressed={lang === "en"}
                  className={`rounded-md px-2.5 py-1 font-semibold ${lang === "en"
                    ? "bg-indigo-600 text-white"
                    : "text-slate-600 hover:bg-slate-200/70"
                    }`}
                  className={`rounded-lg px-3 py-1.5 font-semibold transition ${lang === "en"
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
                  className={`rounded-lg px-3 py-1.5 font-semibold transition ${lang === "bn"
                    ? "bg-indigo-600 text-white"
                    : "text-slate-600 hover:bg-slate-200/70"
                    }`}
                >
                  বাংলা
                </button>
              </div>
            </div>

            {fromOnboarding && !session ? (
              <div
                role="status"
                className="tf-scale-in rounded-2xl border border-teal-200 bg-teal-50/80 px-5 py-4 text-sm text-teal-950 sm:text-base"
              >
                <p className="font-semibold">
                  {isBn
                    ? "স্বাগতম! তোমার সেটআপ সম্পন্ন হয়েছে।"
                    : "Welcome! Your preferences are saved."}
                </p>
                <p className="mt-1 text-teal-900">
                  {isBn
                    ? `নিচে থেকে ${langLabel} অ্যাডাপ্টিভ ডায়াগনস্টিক শুরু করলে আমরা তোমার বাস্তব দক্ষতা অনুযায়ী সঠিক ট্র্যাক নির্ধারণ করে দেব।`
                    : `Start your ${langLabel} adaptive diagnostic below to receive an evidence-based track placement, or switch to your dashboard anytime.`}
                </p>
              </div>
            ) : null}

            {errorMsg ? (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-900"
                className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"
              >
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
                <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600" />
                <span>{errorMsg}</span>
              </div>
            ) : null}

            {/* Last Feedback Banner */}
            {session?.last_feedback ? (
              <div
                role="status"
                className={`rounded-xl border p-4 text-xs ${session.last_feedback.is_correct
                  ? "border-emerald-200 bg-emerald-50/70 text-emerald-950"
                  : "border-amber-200 bg-amber-50/70 text-amber-950"
                  }`}
                className={`tf-scale-in rounded-2xl border p-4 text-sm ${session.last_feedback.is_correct
                  ? "border-emerald-200 bg-emerald-50/80 text-emerald-950"
                  : "border-amber-200 bg-amber-50/80 text-amber-950"
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
                      Sandbox: {session.last_feedback.passed_tests}/
                      {session.last_feedback.total_tests} passed (
                      {session.last_feedback.execution_verdict})
                    </Badge>
                  ) : null}
                </div>
                <p className="mt-1">
                  <p className="mt-1.5 leading-relaxed">
                    {isBn
                      ? session.last_feedback.feedback_bn
                      : session.last_feedback.feedback_en}
                  </p>
                  {session.last_feedback.adaptive_action ? (
                    <p className="mt-1.5 flex items-center gap-1.5 font-semibold text-indigo-800">
                      <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                      <p className="mt-2 flex items-center gap-1.5 font-semibold text-indigo-800">
                        <Sparkles className="h-4 w-4" aria-hidden="true" />
                        <span>{session.last_feedback.adaptive_action}</span>
                      </p>
          ) : null}
                    </div>
                  ) : null}

                  {/* Start Card when no active session */}
                  {/* Start Cards when no active session */}
                  {!session ? (
                    <div className="space-y-4 rounded-2xl border border-indigo-200 bg-white p-6 shadow-sm">
                      <h2 className="text-base font-bold text-slate-900">
                        Ready to discover your actual {langLabel} baseline?
                      </h2>
                      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                        {Object.entries(DOMAIN_LABELS).map(([slug, label]) => (
              <div
                key={slug}
                className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-700"
        <div className="grid gap-5 lg:grid-cols-2">
          {/* Option A: Beginner Short Foundation Readiness Check */}
          <div
            className={`tf-card-interactive flex flex-col justify-between rounded-2xl border p-6 shadow-sm ${
              recommendedMode === "readiness"
                ? "border-teal-500 bg-teal-50/30 ring-1 ring-teal-500"
                : "border-slate-200 bg-white"
            }`}
          >
            <div className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Badge variant="teal">
                  {isBn ? "নতুনদের জন্য · ~৫ মিনিট" : "Beginner Friendly · ~5 min"}
                </Badge>
                {recommendedMode === "readiness" ? (
                  <Badge variant="emerald">
                    {isBn ? "তোমার জন্য প্রস্তাবিত" : "Recommended for You"}
                  </Badge>
                ) : null}
              </div>
              <h2 className="text-xl font-bold text-slate-900">
                {isBn
                  ? `সংক্ষিপ্ত ${langLabel} প্রস্তুতি যাচাই (৪ ডোমেইন)`
                  : `Short ${langLabel} Foundation Readiness Check`}
              </h2>
              <p className="text-sm leading-relaxed text-slate-600 sm:text-base">
                {isBn
                  ? "ভেরিয়েবল, সিনট্যাক্স ডিবাগিং, কন্ডিশন এবং লুপ—এই ৪টি মূল বিষয়ে সংক্ষিপ্ত যাচাই। প্রাথমিক লেসনের পর নিজের ভিত্তি নিশ্চিত করতে আদর্শ।"
                  : "Focused 4-domain check covering variables, syntax debugging, conditions, and loops. Designed for beginners after introductory lessons without overwhelming advanced prompts."}
              </p>
              <div className="grid grid-cols-2 gap-2 pt-1">
                {[
                  "variables",
                  "syntax_runtime_debugging",
                  "conditions",
                  "loop_boundaries",
                ].map((slug) => (
                  <div
                    key={slug}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700"
                  >
                    {DOMAIN_LABELS[slug]}
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-5 pt-2">
              <button
                type="button"
                disabled={loading}
                data-testid="start-readiness-check-btn"
                onClick={() => {
                  void handleStartDiagnostic("readiness");
                }}
                className="tf-btn-press inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl bg-teal-600 px-5 py-2.5 text-base font-semibold text-white transition hover:bg-teal-500 disabled:opacity-60 sm:w-auto"
              >
                {label}
                {loading && startingMode === "readiness" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" aria-hidden="true" />
                )}
                <span>
                  {isBn
                    ? "সংক্ষিপ্ত প্রস্তুতি যাচাই শুরু করো"
                    : "Start Short Readiness Check"}
                </span>
              </button>
            </div>
          </div>

          {/* Option B: Experienced Student Full 8-Domain Adaptive Diagnostic */}
          <div
            className={`tf-card-interactive flex flex-col justify-between rounded-2xl border p-6 shadow-sm ${
              recommendedMode === "full"
                ? "border-indigo-500 bg-indigo-50/25 ring-1 ring-indigo-500"
                : "border-slate-200 bg-white"
            }`}
          >
            <div className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Badge variant="indigo">
                  {isBn ? "পূর্ণ যাচাই · ৮ ডোমেইন · ~১০ মিনিট" : "Full Placement · 8 Domains · ~10 min"}
                </Badge>
                {recommendedMode === "full" ? (
                  <Badge variant="emerald">
                    {isBn ? "প্রস্তাবিত" : "Recommended"}
                  </Badge>
                ) : null}
              </div>
            ))}
              <h2 className="text-xl font-bold text-slate-900">
                {isBn
                  ? `পূর্ণ ৮-ডোমেইন ${langLabel} অ্যাডাপ্টিভ ডায়াগনস্টিক`
                  : `Full 8-Domain ${langLabel} Adaptive Diagnostic`}
              </h2>
              <p className="text-sm leading-relaxed text-slate-600 sm:text-base">
                {isBn
                  ? "অ্যাডাপ্টিভ ফলো-আপ এবং আসল স্যান্ডবক্স কোড এক্সিকিউশনসহ সব ৮টি ডোমেইনে দক্ষতা যাচাই করে চারটি ট্র্যাকের মধ্যে সঠিক অবস্থান নির্ধারণ করে।"
                  : `Evaluates all 8 ${langLabel} domains with adaptive follow-ups and live sandbox coding checks to recommend Absolute Beginner, Basic University, Intermediate, or Advanced placement.`}
              </p>
              <div className="grid grid-cols-2 gap-2 pt-1">
                {Object.entries(DOMAIN_LABELS).map(([slug, label]) => (
                  <div
                    key={slug}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
                  >
                    {label}
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-5 pt-2">
              <button
                type="button"
                disabled={loading}
                data-testid="start-full-diagnostic-btn"
                onClick={() => {
                  void handleStartDiagnostic("full");
                }}
                className="tf-btn-press inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-base font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-60 sm:w-auto"
              >
                {loading && startingMode === "full" ? (
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
                                  <div className="tf-scale-in space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-7">
                                    <div className="space-y-3 border-b border-slate-100 pb-4">
                                      <div className="flex flex-wrap items-center justify-between gap-2">
                                        <div className="flex flex-wrap items-center gap-2">
                                          <Badge variant={session.assessment_mode === "readiness" ? "teal" : "indigo"}>
                                            {session.assessment_mode === "readiness"
                                              ? "Short Readiness Check"
                                              : "8-Domain Diagnostic"}
                                          </Badge>
              ) : null}
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
                                              <Code2 className="h-3.5 w-3.5" aria-hidden="true" />
                                              <span>Real Judge0 Execution Check</span>
                                            </Badge>
                                          ) : null}
                                        </div>
                                        <span className="text-sm font-medium text-slate-600">
                                          Answered {session.answered_count} · Remaining{" "}
                                          {session.remaining_count}
                                          {session.adaptive_followups_added > 0
                                            ? ` · +${session.adaptive_followups_added} adaptive`
                                            : ""}
                                        </span>
                                      </div>
                                      <span className="text-xs font-medium text-slate-500">
                                        Answered {session.answered_count} · Remaining{" "}
                                        {session.remaining_count}
                                        {session.adaptive_followups_added > 0
                                          ? ` · +${session.adaptive_followups_added} adaptive`
                                          : ""}
                                      </span>
                                      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                                        <div
                                          className="tf-progress-fill h-full rounded-full bg-gradient-to-r from-indigo-600 to-teal-500"
                                          style={{
                                            width: `${Math.max(
                                              8,
                                              Math.round(
                                                (session.answered_count /
                                                  Math.max(
                                                    session.answered_count + session.remaining_count,
                                                    1,
                                                  )) *
                                                100,
                                              ),
                                            )}%`,
                                          }}
                                        />
                                      </div>
                                    </div>

                                    <h2 className="text-base font-bold leading-relaxed text-slate-900">
                                      <h2 className="text-lg font-bold leading-relaxed text-slate-900 sm:text-xl">
                                        {isBn
                                          ? session.current_question.prompt_bn
                                          : session.current_question.prompt_en}
                                      </h2>

                                      {session.current_question.code_snippet ? (
                                        <pre className="overflow-x-auto rounded-xl bg-slate-900 p-4 font-mono text-xs leading-relaxed text-slate-100">
                                          <pre className="overflow-x-auto rounded-xl bg-slate-900 p-4 font-mono text-sm leading-relaxed text-slate-100">
                                            {session.current_question.code_snippet}
                                          </pre>
          ) : null}

                                          {session.current_question.question_type === "mcq" ? (
                                            <fieldset className="space-y-2.5">
                                              <fieldset className="space-y-3">
                                                <legend className="sr-only">Diagnostic options</legend>
                                                {session.current_question.options.map((opt) => (
                                                  <label
                                                    key={opt.id}
                                                    className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3.5 text-sm transition ${selectedOption === opt.id
                                                      ? "border-indigo-600 bg-indigo-50/60"
                                                      : "border-slate-200 bg-white hover:bg-slate-50"
                                                      }`}
                                                    className={`flex cursor-pointer items-start gap-3.5 rounded-xl border p-4 text-base transition ${selectedOption === opt.id
                                                      ? "border-indigo-600 bg-indigo-50/70 ring-1 ring-indigo-600"
                                                      : "border-slate-200 bg-white hover:border-indigo-300 hover:bg-slate-50"
                                                      }`}
                                                  >
                                                    <input
                                                      type="radio"
                                                      name="diag-option"
                                                      value={opt.id}
                                                      checked={selectedOption === opt.id}
                                                      onChange={() => setSelectedOption(opt.id)}
                                                      className="mt-1"
                                                      className="mt-1 h-4 w-4 accent-indigo-600"
                                                    />
                                                    <span className="text-slate-800">
                                                      <span className="leading-relaxed text-slate-800">
                                                        {isBn ? opt.text_bn : opt.text_en}
                                                      </span>
                                                  </label>
                                                ))}
                                              </fieldset>
                                              ) : (
                                              <div className="overflow-hidden rounded-xl border border-slate-200">
                                                <div className="bg-slate-900 px-3.5 py-2 text-xs font-semibold text-slate-200">
                                                  <div className="bg-slate-900 px-4 py-2.5 text-sm font-semibold text-slate-200">
                                                    {questionLangLabel} Execution Editor (Evaluated in Real Sandbox)
                                                  </div>
                                                  <CodeEditor
                                                    language={questionMonacoLang}
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
                                                    className="tf-btn-press inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-base font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
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
                                                            ? "Running in Sandbox..."
                                                            : "Evaluating..."
                                                          : "Submit Answer"}
                                                    </span>
                                                  </button>
                                                </div>
                                              </div>
                                              ) : (
                                              /* Completed Diagnostic Evidence Report */
                                              <div className="space-y-5 rounded-2xl border border-emerald-200 bg-white p-6 shadow-sm">
                                                <div className="tf-celebrate-pop space-y-5 rounded-2xl border border-emerald-200 bg-white p-6 shadow-sm sm:p-7">
                                                  <div className="flex flex-wrap items-center justify-between gap-3">
                                                    <div className="flex items-center gap-2.5">
                                                      <Award className="h-6 w-6 text-emerald-600" aria-hidden="true" />
                                                      <div className="flex items-center gap-3">
                                                        <Award className="h-7 w-7 text-emerald-600" aria-hidden="true" />
                                                        <div>
                                                          <h2 className="text-lg font-bold text-slate-900">
                                                            <h2 className="text-xl font-bold text-slate-900">
                                                              Diagnostic Completed — Evidence-Based Track Placement
                                                            </h2>
                                                            <p className="text-xs text-slate-600">
                                                              <p className="text-sm text-slate-600">
                                                                {session.assessment_mode === "readiness"
                                                                  ? "Short Foundation Readiness Check · "
                                                                  : "Full 8-Domain Adaptive Diagnostic · "}
                                                                Answered {session.answered_count} checks (including{" "}
                                                                {session.adaptive_followups_added} adaptive follow-ups)
                                                              </p>
                                                            </div>
                                                        </div>
                                                        {session.recommended_track_slug ? (
                                                          <Badge variant="emerald">
                                                            <span className="capitalize">
                                                              <span className="text-sm capitalize">
                                                                Recommended Track:{" "}
                                                                {session.recommended_track_slug.replaceAll("_", " ")}
                                                              </span>
                                                          </Badge>
                                                        ) : null}
                                                      </div>

                                                      {session.recommendation_rationale ? (
                                                        <p className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 text-sm text-emerald-950">
                                                          <p className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4 text-base leading-relaxed text-emerald-950">
                                                            {session.recommendation_rationale}
                                                          </p>
          ) : null}

                                                          <div className="grid gap-3 sm:grid-cols-2">
                                                            <div className="grid gap-3.5 sm:grid-cols-2">
                                                              {session.domain_evidence.map((ev) => (
              <div
                key={ev.domain_slug}
                className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5 text-xs"
                className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 text-sm"
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
                <p className="mt-1.5 text-slate-600">
                  Observed: <strong>{ev.observed_correct}</strong> /{" "}
                  <strong>{ev.observed_attempts}</strong>
                  {ev.execution_verified ? " · Judge0 Execution Verified" : ""}
                  {ev.execution_verified ? " · Sandbox Execution Verified" : ""}
                </p>
                <p className="mt-1 text-slate-700">
                <p className="mt-1 leading-relaxed text-slate-700">
                  {isBn ? ev.note_bn : ev.note_en}
                </p>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-3 pt-2">
            {session.next_recommended_action ? (
              <Link
                href={session.next_recommended_action.href}
                className="tf-btn-press inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-teal-500"
              >
                <span>
                  {isBn
                    ? session.next_recommended_action.cta_label_bn
                    : session.next_recommended_action.cta_label_en}
                </span>
              </Link>
            ) : null}
            <Link
              href="/student"
              className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500"
              className="tf-btn-press inline-flex min-h-[44px] items-center gap-1.5 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"
            >
              <span>View Updated Skill Graph &amp; Recommendations</span>
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
            <Link
              href="/student/lessons"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-800 hover:bg-slate-50"
              className="tf-btn-press inline-flex min-h-[44px] items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50"
            >
              <span>Start {langLabel} Guided Lessons</span>
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
                    className={`h-3.5 w-3.5 ${item.status === "completed"
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
                  {formatUtcDateTime(item.started_at)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
