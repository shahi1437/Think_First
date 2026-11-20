"use client";

import {
  AlertCircle,
  Award,
  CheckCircle2,
  Loader2,
  Lock,
  Send,
  ShieldCheck,
  Unlock,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { VerdictBadge } from "@/components/ui/verdict-badge";
import { CodeEditor } from "@/features/workspace/code-editor";
import {
  fetchProblemDetail,
  submitTransferVerificationAttempt,
} from "@/lib/api-client";
import type {
  TransferChallengeSummary,
  VerificationAttemptView,
} from "@/types/mentor";
import type { StudentProblemDetail } from "@/types/problems";

interface TransferVerificationPanelProps {
  accessToken: string;
  challenge: TransferChallengeSummary | null;
  latestAcceptedSubmissionId: string | null;
  usePlainEditor?: boolean;
  onRefreshChallenge?: () => Promise<void>;
  onSubmitAttempt?: (
    linkId: string,
    payload: {
      source_submission_id?: string | null;
      language_slug: string;
      source_code: string;
      student_explanation: string;
    },
  ) => Promise<VerificationAttemptView>;
}

export function TransferVerificationPanel({
  accessToken,
  challenge,
  latestAcceptedSubmissionId,
  usePlainEditor = false,
  onRefreshChallenge,
  onSubmitAttempt,
}: TransferVerificationPanelProps) {
  const [transferProblem, setTransferProblem] =
    useState<StudentProblemDetail | null>(null);
  const [loadedProblemId, setLoadedProblemId] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [explanation, setExplanation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submittedAttempt, setSubmittedAttempt] =
    useState<VerificationAttemptView | null>(null);

  const latestAttempt = submittedAttempt ?? challenge?.latest_attempt ?? null;
  const loadingProblem = Boolean(
    challenge?.unlocked &&
      loadedProblemId !== challenge.transfer_problem_id &&
      !errorMessage,
  );

  useEffect(() => {
    if (!challenge || !challenge.unlocked) return;
    let cancelled = false;
    fetchProblemDetail(accessToken, challenge.transfer_problem_id)
      .then((detail) => {
        if (cancelled) return;
        setTransferProblem(detail);
        setLoadedProblemId(challenge.transfer_problem_id);
        const pyVariant =
          detail.variants.find((v) => v.language_slug === "python") ??
          detail.variants[0];
        setCode((prev) => (prev ? prev : (pyVariant?.starter_code ?? "")));
      })
      .catch(() => {
        if (!cancelled) {
          setLoadedProblemId(challenge.transfer_problem_id);
          setErrorMessage(
            "Could not load the transfer challenge details right now.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [accessToken, challenge]);

  if (!challenge) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5 text-center text-xs text-slate-600">
        No unseen transfer verification challenge is linked to this problem yet.
      </div>
    );
  }

  if (!challenge.unlocked) {
    return (
      <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-5">
        <div className="flex items-center gap-2 text-slate-800">
          <Lock className="h-4 w-4 text-slate-500" aria-hidden="true" />
          <h3 className="text-sm font-bold">
            Independent Transfer Verification (Locked)
          </h3>
        </div>
        <p className="text-xs leading-relaxed text-slate-600">
          {challenge.unlock_reason}
        </p>
        <div className="rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-700">
          <p className="font-semibold text-slate-900">
            Upcoming Skill Check: {challenge.transfer_problem_title}
          </p>
          <p className="mt-1 text-slate-600">
            Skill focus: <code>{challenge.skill_focus}</code> · Max AI hints
            allowed: <strong>{challenge.max_hints_allowed}</strong>
          </p>
        </div>
      </div>
    );
  }

  async function handleSubmitTransfer(e: React.FormEvent) {
    e.preventDefault();
    if (!challenge) return;
    if (explanation.trim().length < 10) {
      setErrorMessage(
        "Please write at least 10 characters explaining how you applied the concept independently.",
      );
      return;
    }
    setErrorMessage(null);
    setSubmitting(true);
    try {
      const payload = {
        source_submission_id: latestAcceptedSubmissionId,
        language_slug: "python",
        source_code: code,
        student_explanation: explanation.trim(),
      };
      const attempt = onSubmitAttempt
        ? await onSubmitAttempt(challenge.verification_link_id, payload)
        : await submitTransferVerificationAttempt(
            accessToken,
            challenge.verification_link_id,
            payload,
          );
      setSubmittedAttempt(attempt);
      if (onRefreshChallenge) {
        await onRefreshChallenge();
      }
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Transfer verification submission failed.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-teal-200 bg-teal-50/70 px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <Unlock className="h-4 w-4 text-teal-700" aria-hidden="true" />
          <h3 className="text-sm font-bold text-teal-950">
            {challenge.transfer_problem_title}
          </h3>
          <Badge variant="teal">
            <ShieldCheck className="h-3 w-3" aria-hidden="true" />
            <span>
              Zero-Hint Independent Check ({challenge.max_hints_allowed} hints)
            </span>
          </Badge>
        </div>
        <Badge variant="neutral">
          <span>{challenge.skill_focus}</span>
        </Badge>
      </div>

      <p className="text-xs leading-relaxed text-slate-700">
        {challenge.instructions_md}
      </p>

      {/* Persisted Factual Outcome Banner */}
      {latestAttempt ? (
        <div
          role="status"
          className={`rounded-xl border p-3.5 text-xs ${
            latestAttempt.outcome === "verified_independent"
              ? "border-emerald-300 bg-emerald-50 text-emerald-950"
              : "border-amber-300 bg-amber-50 text-amber-950"
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2 font-bold">
              {latestAttempt.outcome === "verified_independent" ? (
                <Award
                  className="h-4 w-4 text-emerald-700"
                  aria-hidden="true"
                />
              ) : (
                <CheckCircle2
                  className="h-4 w-4 text-amber-700"
                  aria-hidden="true"
                />
              )}
              <span>
                {latestAttempt.outcome === "verified_independent"
                  ? "Verified Independent Understanding"
                  : "Attempted — Not Yet Verified"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <VerdictBadge verdict={latestAttempt.verdict} />
              <span className="font-semibold">
                {latestAttempt.passed_tests} / {latestAttempt.total_tests}{" "}
                Judge0 tests
              </span>
            </div>
          </div>
          <p className="mt-1.5">{latestAttempt.summary_message}</p>
        </div>
      ) : null}

      {errorMessage ? (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-900"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
          <span>{errorMessage}</span>
        </div>
      ) : null}

      {loadingProblem ? (
        <div className="flex items-center gap-2 rounded-lg bg-slate-50 p-4 text-xs text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
          <span>Loading unseen transfer challenge...</span>
        </div>
      ) : transferProblem ? (
        <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-3.5 text-xs">
          <div className="whitespace-pre-line leading-relaxed text-slate-800">
            {transferProblem.statement_md}
          </div>
          {transferProblem.examples.length > 0 ? (
            <div className="grid gap-2 sm:grid-cols-2">
              {transferProblem.examples.map((ex, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-2.5"
                >
                  <p className="font-semibold text-slate-600">
                    Example {i + 1} Input
                  </p>
                  <pre className="mt-1 overflow-x-auto rounded bg-white p-1.5 font-mono text-slate-900">
                    {ex.input}
                  </pre>
                  <p className="mt-1.5 font-semibold text-slate-600">Output</p>
                  <pre className="mt-1 overflow-x-auto rounded bg-white p-1.5 font-mono text-slate-900">
                    {ex.output}
                  </pre>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      <form
        onSubmit={(e) => void handleSubmitTransfer(e)}
        className="space-y-3"
      >
        <div className="overflow-hidden rounded-xl border border-slate-200">
          <div className="flex items-center justify-between bg-slate-900 px-3 py-2 text-xs text-slate-200">
            <span className="font-semibold">
              Transfer Challenge Editor (Python 3 · No Hints)
            </span>
          </div>
          <CodeEditor
            language="python"
            value={code}
            onChange={setCode}
            usePlainTextarea={usePlainEditor}
          />
        </div>

        <div>
          <label
            htmlFor="transfer-explanation"
            className="block text-xs font-semibold text-slate-700"
          >
            Explain your independent solution (required, min 10 chars)
          </label>
          <textarea
            id="transfer-explanation"
            rows={2}
            value={explanation}
            onChange={(e) => setExplanation(e.target.value)}
            placeholder="Explain why your boundary/initialization logic handles all edge cases..."
            className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-teal-600 focus:outline-none"
          />
        </div>

        <button
          type="submit"
          disabled={submitting || !code.trim()}
          className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-teal-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Send className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          <span>
            {submitting
              ? "Verifying on Judge0..."
              : "Submit Independent Verification"}
          </span>
        </button>
      </form>
    </div>
  );
}
