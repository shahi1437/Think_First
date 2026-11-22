"use client";

import {
  AlertCircle,
  ArrowRight,
  Award,
  CheckCircle2,
  Loader2,
  Lock,
  Send,
  ShieldCheck,
  Unlock,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { VerdictBadge } from "@/components/ui/verdict-badge";
import { CodeEditor } from "@/features/workspace/code-editor";
import {
  fetchProblemDetail,
  submitTransferVerificationAttempt,
} from "@/lib/api-client";
import {
  getLanguageDisplayName,
  getMonacoLanguageForSlug,
} from "@/lib/languages";
import type {
  TransferChallengeSummary,
  VerificationAttemptView,
} from "@/types/mentor";
import type { StudentProblemDetail } from "@/types/problems";

interface TransferVerificationPanelProps {
  accessToken: string;
  challenge: TransferChallengeSummary | null;
  latestAcceptedSubmissionId: string | null;
  activeLanguageSlug?: string;
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
  activeLanguageSlug = "python",
  usePlainEditor = false,
  onRefreshChallenge,
  onSubmitAttempt,
}: TransferVerificationPanelProps) {
  const [transferProblem, setTransferProblem] =
    useState<StudentProblemDetail | null>(null);
  const [loadedProblemId, setLoadedProblemId] = useState<string | null>(null);
  const [transferLang, setTransferLang] = useState<string>(activeLanguageSlug);
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
        const preferredVariant =
          detail.variants.find((v) => v.language_slug === activeLanguageSlug) ??
          detail.variants[0];
        if (preferredVariant) {
          setTransferLang(preferredVariant.language_slug);
          setCode((prev) => (prev ? prev : (preferredVariant.starter_code ?? "")));
        }
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
  }, [accessToken, activeLanguageSlug, challenge]);

  if (!challenge) {
    return (
      <div className="space-y-3 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center">
        <p className="text-sm font-medium text-slate-700">
          No unseen transfer verification challenge is linked to this problem yet.
        </p>
        <Link
          href="/student"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-indigo-700 hover:underline"
        >
          <span>Return to Continue Learning</span>
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      </div>
    );
  }

  if (!challenge.unlocked) {
    return (
      <div className="space-y-3.5 rounded-2xl border border-slate-200 bg-slate-50 p-5 sm:p-6">
        <div className="flex items-center gap-2 text-slate-800">
          <Lock className="h-5 w-5 text-slate-500" aria-hidden="true" />
          <h3 className="text-base font-bold">
            Independent Transfer Verification (Locked)
          </h3>
        </div>
        <p className="text-sm leading-relaxed text-slate-700">
          {challenge.unlock_reason}
        </p>
        <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
          <p className="font-semibold text-slate-900">
            Upcoming Skill Check: {challenge.transfer_problem_title}
          </p>
          <p className="mt-1.5 text-slate-600">
            Skill focus: <code>{challenge.skill_focus}</code> · Max AI hints
            allowed: <strong>{challenge.max_hints_allowed}</strong>
          </p>
        </div>
      </div>
    );
  }

  const availableVariants = transferProblem?.variants ?? [];
  const requestedVariantSupported =
    availableVariants.length === 0 ||
    availableVariants.some((v) => v.language_slug === activeLanguageSlug);
  const effectiveLangLabel = getLanguageDisplayName(transferLang);
  const effectiveMonacoLang = getMonacoLanguageForSlug(transferLang);

  function handleTransferLangChange(nextSlug: string) {
    setTransferLang(nextSlug);
    const matched = availableVariants.find((v) => v.language_slug === nextSlug);
    if (matched) {
      setCode(matched.starter_code ?? "");
    }
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
        language_slug: transferLang,
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
    <div className="tf-animate-enter space-y-4">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-teal-200 bg-teal-50/80 px-4 py-3.5">
        <div className="flex flex-wrap items-center gap-2">
          <Unlock className="h-4 w-4 text-teal-700" aria-hidden="true" />
          <h3 className="text-base font-bold text-teal-950">
            {challenge.transfer_problem_title}
          </h3>
          <Badge variant="teal">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
            <span>
              Zero-Hint Independent Check ({challenge.max_hints_allowed} hints)
            </span>
          </Badge>
        </div>
        <Badge variant="neutral">
          <span>{challenge.skill_focus}</span>
        </Badge>
      </div>

      <p className="text-sm leading-relaxed text-slate-700">
        {challenge.instructions_md}
      </p>

      {/* Honest notification if the requested active language has no variant on this challenge */}
      {!requestedVariantSupported && availableVariants.length > 0 ? (
        <div
          role="note"
          className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
          <span>
            This unseen transfer challenge does not yet include a{" "}
            <strong>{getLanguageDisplayName(activeLanguageSlug)}</strong>{" "}
            variant. You can complete it in{" "}
            <strong>{effectiveLangLabel}</strong> below, or return to{" "}
            <Link href="/student/problems" className="font-semibold underline">
              Problem Bank
            </Link>{" "}
            for additional practice.
          </span>
        </div>
      ) : null}

      {/* Persisted Factual Outcome Banner */}
      {latestAttempt ? (
        <div
          role="status"
          className={`tf-celebrate-pop rounded-2xl border p-4 text-sm ${
            latestAttempt.outcome === "verified_independent"
              ? "border-emerald-300 bg-emerald-50 text-emerald-950"
              : "border-amber-300 bg-amber-50 text-amber-950"
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2 font-bold">
              {latestAttempt.outcome === "verified_independent" ? (
                <Award
                  className="h-5 w-5 text-emerald-700"
                  aria-hidden="true"
                />
              ) : (
                <CheckCircle2
                  className="h-5 w-5 text-amber-700"
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
          <p className="mt-2 leading-relaxed">{latestAttempt.summary_message}</p>
          {latestAttempt.outcome === "verified_independent" ? (
            <div className="mt-3">
              <Link
                href="/student"
                className="tf-btn-press inline-flex items-center gap-1.5 rounded-xl bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-600"
              >
                <span>Continue Next Learning Step</span>
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
          ) : null}
        </div>
      ) : null}

      {errorMessage ? (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-900"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
          <span>{errorMessage}</span>
        </div>
      ) : null}

      {loadingProblem ? (
        <div className="flex items-center gap-2.5 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
          <span>Loading unseen transfer challenge...</span>
        </div>
      ) : transferProblem ? (
        <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 text-sm">
          <div className="whitespace-pre-line leading-relaxed text-slate-800">
            {transferProblem.statement_md}
          </div>
          {transferProblem.examples.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {transferProblem.examples.map((ex, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm"
                >
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Example {i + 1} Input
                  </p>
                  <pre className="mt-1 overflow-x-auto rounded-lg bg-white p-2 font-mono text-sm text-slate-900">
                    {ex.input}
                  </pre>
                  <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Output
                  </p>
                  <pre className="mt-1 overflow-x-auto rounded-lg bg-white p-2 font-mono text-sm text-slate-900">
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
        className="space-y-3.5"
      >
        <div className="overflow-hidden rounded-xl border border-slate-200">
          <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-900 px-3.5 py-2.5 text-sm text-slate-200">
            <span className="font-semibold">
              Transfer Challenge Editor ({effectiveLangLabel} · No Hints)
            </span>
            {availableVariants.length > 1 ? (
              <label className="inline-flex items-center gap-2 text-xs text-slate-300">
                <span>Language:</span>
                <select
                  aria-label="Transfer challenge language"
                  value={transferLang}
                  onChange={(e) => handleTransferLangChange(e.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-semibold text-white focus:border-teal-400 focus:outline-none"
                >
                  {availableVariants.map((variant) => (
                    <option
                      key={variant.language_slug}
                      value={variant.language_slug}
                    >
                      {getLanguageDisplayName(variant.language_slug)}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
          </div>
          <CodeEditor
            language={effectiveMonacoLang}
            value={code}
            onChange={setCode}
            usePlainTextarea={usePlainEditor}
          />
        </div>

        <div>
          <label
            htmlFor="transfer-explanation"
            className="block text-sm font-semibold text-slate-800"
          >
            Explain your independent solution (required, min 10 chars)
          </label>
          <textarea
            id="transfer-explanation"
            rows={2}
            value={explanation}
            onChange={(e) => setExplanation(e.target.value)}
            placeholder="Explain why your boundary/initialization logic handles all edge cases..."
            className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 focus:border-teal-600 focus:outline-none"
          />
        </div>

        <button
          type="submit"
          disabled={submitting || !code.trim()}
          className="tf-btn-press inline-flex min-h-[44px] items-center gap-2 rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-teal-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" aria-hidden="true" />
          )}
          <span>
            {submitting
              ? "Verifying in Sandbox..."
              : "Submit Independent Verification"}
          </span>
        </button>
      </form>
    </div>
  );
}
