"use client";

import {
  AlertCircle,
  AlertTriangle,
  BookOpen,
  Bot,
  Brain,
  CheckCircle2,
  Lightbulb,
  Loader2,
  RefreshCw,
  Send,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { sendMentorTurn, startOrResumeMentorSession } from "@/lib/api-client";
import { getLanguageShortLabel } from "@/lib/languages";
import type { MentorSessionDetail } from "@/types/mentor";

interface MentorPanelProps {
  accessToken: string;
  problemId: string;
  latestSubmissionId: string | null;
  latestVerdict: string | null;
  session: MentorSessionDetail | null;
  onSessionChange: (next: MentorSessionDetail) => void;
  onStartSession?: (payload: {
    problem_id: string;
    submission_id?: string | null;
    explanation_language?: "en" | "bn";
  }) => Promise<MentorSessionDetail>;
  onSendTurn?: (
    sessionId: string,
    payload: {
      action: "diagnose" | "respond" | "request_hint";
      submission_id?: string | null;
      student_message?: string;
      requested_hint_level?: 1 | 2 | 3;
      explanation_language?: "en" | "bn";
    },
  ) => Promise<MentorSessionDetail>;
}

const STATE_LABELS: Record<string, string> = {
  awaiting_submission: "Run Code First",
  diagnosing: "Diagnosing",
  asking_question: "Socratic Question",
  awaiting_student_response: "Your Reasoning",
  giving_hint: "Hint Provided",
  awaiting_revision: "Revise & Re-Run",
  verifying: "Ready for Transfer Check",
  completed: "Completed",
  fallback: "Guided Fallback",
};

export function MentorPanel({
  accessToken,
  problemId,
  latestSubmissionId,
  latestVerdict,
  session,
  onSessionChange,
  onStartSession,
  onSendTurn,
}: MentorPanelProps) {
  const [language, setLanguage] = useState<"en" | "bn">(
    session?.explanation_language ?? "en",
  );
  const [studentMessage, setStudentMessage] = useState("");
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showAllCitations, setShowAllCitations] = useState(true);

  async function ensureSession(): Promise<MentorSessionDetail> {
    if (session) return session;
    const created = onStartSession
      ? await onStartSession({
          problem_id: problemId,
          submission_id: latestSubmissionId,
          explanation_language: language,
        })
      : await startOrResumeMentorSession(accessToken, {
          problem_id: problemId,
          submission_id: latestSubmissionId,
          explanation_language: language,
        });
    onSessionChange(created);
    return created;
  }

  async function handleDiagnoseLatest() {
    setErrorMessage(null);
    setLoadingAction("diagnose");
    try {
      if (!session) {
        await ensureSession();
      } else {
        const updated = onSendTurn
          ? await onSendTurn(session.id, {
              action: "diagnose",
              submission_id: latestSubmissionId,
              explanation_language: language,
            })
          : await sendMentorTurn(accessToken, session.id, {
              action: "diagnose",
              submission_id: latestSubmissionId,
              explanation_language: language,
            });
        onSessionChange(updated);
      }
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Could not analyze submission right now. Please retry.",
      );
    } finally {
      setLoadingAction(null);
    }
  }

  async function handleRequestHint(level: 1 | 2 | 3) {
    setErrorMessage(null);
    setLoadingAction(`hint-${level}`);
    try {
      const active = await ensureSession();
      const updated = onSendTurn
        ? await onSendTurn(active.id, {
            action: "request_hint",
            submission_id: latestSubmissionId,
            requested_hint_level: level,
            explanation_language: language,
          })
        : await sendMentorTurn(accessToken, active.id, {
            action: "request_hint",
            submission_id: latestSubmissionId,
            requested_hint_level: level,
            explanation_language: language,
          });
      onSessionChange(updated);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Could not load hint.",
      );
    } finally {
      setLoadingAction(null);
    }
  }

  async function handleStudentReply(e: React.FormEvent) {
    e.preventDefault();
    if (!studentMessage.trim()) return;
    setErrorMessage(null);
    setLoadingAction("respond");
    try {
      const active = await ensureSession();
      const updated = onSendTurn
        ? await onSendTurn(active.id, {
            action: "respond",
            submission_id: latestSubmissionId,
            student_message: studentMessage.trim(),
            explanation_language: language,
          })
        : await sendMentorTurn(accessToken, active.id, {
            action: "respond",
            submission_id: latestSubmissionId,
            student_message: studentMessage.trim(),
            explanation_language: language,
          });
      setStudentMessage("");
      onSessionChange(updated);
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Could not send response.",
      );
    } finally {
      setLoadingAction(null);
    }
  }

  const diagnosis = session?.latest_diagnosis ?? null;
  const citations = session?.latest_citations ?? [];
  const hintsUsed = session?.hints_used ?? 0;
  const maxHints = session?.max_hints ?? 3;
  const isBangla = language === "bn";

  return (
    <div
      className={`space-y-4 ${isBangla ? "leading-relaxed" : ""}`}
      lang={language}
    >
      {/* Top Bar: Title, Provider Mode Badge, Language Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-indigo-200 bg-indigo-50/50 px-3.5 py-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <Bot className="h-4 w-4 text-indigo-700" aria-hidden="true" />
          <h3 className="text-sm font-bold text-indigo-950">
            Socratic AI Mentor
          </h3>
          {session ? (
            <>
              <Badge
                variant={
                  session.provider_mode === "live_llm" ? "teal" : "amber"
                }
              >
                <Sparkles className="h-3 w-3" aria-hidden="true" />
                <span>
                  {session.provider_mode === "live_llm"
                    ? "Live LLM"
                    : "Deterministic Socratic Fallback"}
                </span>
              </Badge>
              <Badge variant="indigo">
                <span>
                  {STATE_LABELS[session.current_state] ?? session.current_state}
                </span>
              </Badge>
            </>
          ) : null}
        </div>

        <div className="flex items-center gap-2">
          <div
            role="group"
            aria-label="Explanation language"
            className="inline-flex rounded-lg border border-indigo-200 bg-white p-0.5 text-xs"
          >
            <button
              type="button"
              onClick={() => setLanguage("en")}
              aria-pressed={language === "en"}
              className={`rounded-md px-2 py-1 font-semibold transition ${
                language === "en"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              English
            </button>
            <button
              type="button"
              onClick={() => setLanguage("bn")}
              aria-pressed={language === "bn"}
              className={`rounded-md px-2 py-1 font-semibold transition ${
                language === "bn"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              বাংলা
            </button>
          </div>

          <button
            type="button"
            disabled={loadingAction !== null || !latestSubmissionId}
            onClick={() => {
              void handleDiagnoseLatest();
            }}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loadingAction === "diagnose" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Brain className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            <span>
              {session ? "Analyze Latest Run" : "Start AI Diagnosis"}
            </span>
          </button>
        </div>
      </div>

      {!latestSubmissionId ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-xs text-slate-600">
          Run or submit your code on Judge0 first. The ML error classifier and
          Socratic AI Mentor analyze real execution evidence — never guesses.
        </div>
      ) : null}

      {errorMessage ? (
        <div
          role="alert"
          className="flex items-start justify-between gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-900"
        >
          <div className="flex items-start gap-2">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
            <span>{errorMessage}</span>
          </div>
          {latestSubmissionId ? (
            <button
              type="button"
              onClick={() => {
                void handleDiagnoseLatest();
              }}
              className="inline-flex shrink-0 items-center gap-1 rounded border border-rose-300 bg-white px-2 py-1 font-semibold text-rose-800 hover:bg-rose-100"
            >
              <RefreshCw className="h-3 w-3" aria-hidden="true" />
              Retry
            </button>
          ) : null}
        </div>
      ) : null}

      {/* Diagnosis Card (Honest ML vs Rule-Based Indicator) */}
      {diagnosis ? (
        <section
          aria-label="Error diagnosis"
          className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <Brain className="h-4 w-4 text-teal-700" aria-hidden="true" />
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                {diagnosis.diagnosis_source === "rule_based"
                  ? `Rule-Based Error Diagnosis (${diagnosis.model_version})`
                  : `ML Error Diagnosis (${diagnosis.model_version})`}
              </span>
              <Badge variant="neutral">
                {getLanguageShortLabel(diagnosis.language_slug)}
              </Badge>
            </div>
            <Badge variant={diagnosis.is_low_confidence ? "amber" : "teal"}>
              <span>
                {Math.round(diagnosis.confidence * 100)}% confidence
              </span>
            </Badge>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-2">
            <p className="text-sm font-bold text-slate-900">
              {diagnosis.predicted_display_name}
            </p>
            <code className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-700">
              {diagnosis.predicted_error_code}
            </code>
          </div>

          {diagnosis.is_low_confidence ? (
            <div
              role="note"
              className="mt-2.5 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
              <span>
                <strong>Low-confidence prediction:</strong>{" "}
                {diagnosis.uncertainty_note ||
                  "Multiple error patterns look plausible. Verify with your own step-by-step trace."}
              </span>
            </div>
          ) : null}

          {diagnosis.top_candidates.length > 0 ? (
            <div className="mt-3 space-y-1.5">
              <p className="text-[11px] font-medium text-slate-500">
                Top candidate error classes
              </p>
              <div className="grid gap-1.5 sm:grid-cols-3">
                {diagnosis.top_candidates.map((cand) => (
                  <div
                    key={cand.error_code}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs"
                  >
                    <div className="flex items-center justify-between gap-1 font-medium text-slate-800">
                      <span className="truncate">{cand.display_name}</span>
                      <span className="tabular-nums text-slate-600">
                        {Math.round(cand.probability * 100)}%
                      </span>
                    </div>
                    <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                      <div
                        className="h-full rounded-full bg-indigo-600"
                        style={{
                          width: `${Math.max(4, Math.round(cand.probability * 100))}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      ) : null}

      {/* Verified RAG Citations Card */}
      {session ? (
        <section
          aria-label="Verified educational references"
          className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5"
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <BookOpen className="h-4 w-4 text-indigo-700" aria-hidden="true" />
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                Verified Knowledge Citations ({citations.length})
              </h4>
            </div>
            {citations.length > 0 ? (
              <button
                type="button"
                onClick={() => setShowAllCitations((v) => !v)}
                className="text-xs font-medium text-indigo-700 hover:underline"
              >
                {showAllCitations ? "Hide" : "Show"}
              </button>
            ) : null}
          </div>

          {citations.length === 0 ? (
            <p className="mt-2 text-xs text-slate-600">
              No approved knowledge excerpt crossed the relevance threshold for
              this run — guidance relies directly on Judge0 execution evidence
              with zero fabricated citations.
            </p>
          ) : showAllCitations ? (
            <div className="mt-2.5 space-y-2">
              {citations.map((cite) => (
                <article
                  key={cite.chunk_id}
                  className="rounded-lg border border-slate-200 bg-white p-2.5 text-xs"
                >
                  <div className="flex flex-wrap items-center justify-between gap-1.5">
                    <p className="font-semibold text-slate-900">
                      {cite.source_title}
                      {cite.heading ? ` — ${cite.heading}` : ""}
                    </p>
                    <Badge variant="neutral">
                      <span>
                        {cite.source_name} v{cite.source_version} · sim{" "}
                        {cite.similarity.toFixed(2)}
                      </span>
                    </Badge>
                  </div>
                  <p className="mt-1.5 leading-relaxed text-slate-700">
                    {cite.excerpt}
                  </p>
                </article>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}

      {/* Progressive 3-Level Hints */}
      {session && latestVerdict !== "accepted" ? (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50/50 px-3.5 py-2.5">
          <div className="flex items-center gap-2 text-xs text-amber-950">
            <Lightbulb className="h-4 w-4 text-amber-600" aria-hidden="true" />
            <span className="font-semibold">
              Progressive Hints ({hintsUsed} / {maxHints} used)
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            {([1, 2, 3] as const).map((lvl) => {
              const disabled =
                loadingAction !== null ||
                hintsUsed >= maxHints ||
                lvl <= hintsUsed;
              return (
                <button
                  key={lvl}
                  type="button"
                  disabled={disabled}
                  onClick={() => {
                    void handleRequestHint(lvl);
                  }}
                  className="inline-flex items-center gap-1 rounded-md border border-amber-300 bg-white px-2.5 py-1 text-xs font-semibold text-amber-900 transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {loadingAction === `hint-${lvl}` ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : null}
                  <span>Hint {lvl}</span>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      {/* Socratic Conversation Log */}
      {session && session.turns.length > 0 ? (
        <div
          aria-label="Socratic dialogue history"
          className="max-h-72 space-y-2.5 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-3"
        >
          {session.turns.map((turn) => {
            const isMentor = turn.role === "mentor";
            const safetyBlocked = Boolean(
              turn.structured_payload?.safety_blocked,
            );
            return (
              <div
                key={turn.id}
                className={`rounded-lg p-3 text-xs leading-relaxed ${
                  isMentor
                    ? "border border-indigo-200 bg-white text-slate-900"
                    : "ml-6 border border-teal-200 bg-teal-50 text-teal-950"
                }`}
              >
                <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-[11px] font-semibold">
                  <span
                    className={isMentor ? "text-indigo-700" : "text-teal-800"}
                  >
                    {isMentor ? "CodeMentor AI" : "You"}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {safetyBlocked ? (
                      <Badge variant="rose">
                        <ShieldAlert className="h-3 w-3" aria-hidden="true" />
                        <span>Guardrail Active</span>
                      </Badge>
                    ) : null}
                    {isMentor && turn.state_after === "verifying" ? (
                      <Badge variant="teal">
                        <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                        <span>Verified Fix</span>
                      </Badge>
                    ) : null}
                  </div>
                </div>
                <p className="whitespace-pre-line">{turn.message_text}</p>
              </div>
            );
          })}
        </div>
      ) : null}

      {/* Student Reasoning Input */}
      {latestSubmissionId ? (
        <form onSubmit={(e) => void handleStudentReply(e)} className="space-y-2">
          <label
            htmlFor="mentor-student-reply"
            className="block text-xs font-semibold text-slate-700"
          >
            {isBangla
              ? "তোমার ধারণা বা ট্রেস এখানে লেখো (AI সরাসরি উত্তর না দিয়ে প্রশ্ন করে সাহায্য করবে)"
              : "Share your reasoning or trace (the mentor guides via questions, never dumps solutions)"}
          </label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              id="mentor-student-reply"
              type="text"
              value={studentMessage}
              onChange={(e) => setStudentMessage(e.target.value)}
              placeholder={
                isBangla
                  ? "যেমন: range(a, b) শেষ সংখ্যা b বাদ দিচ্ছে মনে হচ্ছে..."
                  : "e.g. I think range(a, b) stops before b, so the last number is skipped..."
              }
              className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-indigo-600 focus:outline-none"
            />
            <button
              type="submit"
              disabled={loadingAction !== null || !studentMessage.trim()}
              className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loadingAction === "respond" ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Send className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              <span>Send</span>
            </button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
