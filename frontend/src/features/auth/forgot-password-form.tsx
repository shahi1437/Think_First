"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, CheckCircle2, Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import {
  buildAuthCallbackUrl,
  formatRecoveryRequestError,
} from "@/lib/auth/auth-helpers";
import { PORTAL_LOGIN_PATHS } from "@/lib/auth/roles";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import type { RoleName } from "@/types/identity";

const recoverySchema = z.object({
  email: z.email("Please enter a valid email address."),
});

type RecoveryValues = z.infer<typeof recoverySchema>;

interface ForgotPasswordFormProps {
  portal?: RoleName;
}

const RESEND_COOLDOWN_SECONDS = 60;

export function ForgotPasswordForm({ portal }: ForgotPasswordFormProps) {
  const [serverError, setServerError] = useState<string | null>(null);
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [resending, setResending] = useState(false);
  const [resendNotice, setResendNotice] = useState<string | null>(null);

  const backLoginPath = portal ? PORTAL_LOGIN_PATHS[portal] : "/login";

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = window.setInterval(() => {
      setResendCooldown((prev) => (prev <= 1 ? 0 : prev - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [resendCooldown]);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RecoveryValues>({
    resolver: zodResolver(recoverySchema),
    defaultValues: { email: "" },
  });

  async function requestRecoveryLink(email: string): Promise<string | null> {
    const supabase = createSupabaseBrowserClient();
    const nextTarget = portal
      ? `/reset-password?portal=${portal}`
      : "/reset-password";
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: buildAuthCallbackUrl(nextTarget),
    });
    if (error) {
      return formatRecoveryRequestError(error.message);
    }
    return null;
  }

  async function onSubmit(values: RecoveryValues) {
    setServerError(null);
    setResendNotice(null);
    const normalizedEmail = values.email.trim().toLowerCase();
    try {
      const errorMessage = await requestRecoveryLink(normalizedEmail);
      if (errorMessage) {
        setServerError(errorMessage);
        return;
      }
      setSubmittedEmail(normalizedEmail);
      setResendCooldown(RESEND_COOLDOWN_SECONDS);
    } catch (err) {
      setServerError(
        err instanceof Error
          ? formatRecoveryRequestError(err.message)
          : "Unable to request password reset.",
      );
    }
  }

  async function handleResend() {
    if (!submittedEmail || resendCooldown > 0 || resending) return;
    setResending(true);
    setResendNotice(null);
    setServerError(null);
    try {
      const errorMessage = await requestRecoveryLink(submittedEmail);
      if (errorMessage) {
        setServerError(errorMessage);
      } else {
        setResendNotice(
          "A new recovery request has been submitted. Use only the most recent email link.",
        );
        setResendCooldown(RESEND_COOLDOWN_SECONDS);
      }
    } catch (err) {
      setServerError(
        err instanceof Error
          ? formatRecoveryRequestError(err.message)
          : "Unable to resend password reset right now.",
      );
    } finally {
      setResending(false);
    }
  }

  if (submittedEmail) {
    return (
      <div className="space-y-4 rounded-xl border border-teal-200 bg-teal-50 p-5 text-sm text-teal-950">
        <div className="flex items-center gap-2 font-semibold">
          <CheckCircle2
            className="h-5 w-5 text-teal-700"
            aria-hidden="true"
          />
          <span>Recovery link sent</span>
        </div>
        <p className="leading-relaxed">
          If an account exists for that email address, a password recovery link
          has been sent. Check your inbox (and spam or promotions folder) and
          open the link to set a new password.
        </p>
        <p className="rounded-lg border border-teal-200 bg-white/80 px-3 py-2 text-xs leading-relaxed text-slate-700">
          <strong>Tip for mobile and desktop:</strong> For the smoothest
          verification, open the reset link in the same browser where you
          requested it, and always use the newest recovery email if you
          requested more than one.
        </p>

        {serverError ? (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-900"
          >
            <AlertCircle
              className="mt-0.5 h-4 w-4 shrink-0 text-rose-600"
              aria-hidden="true"
            />
            <span>{serverError}</span>
          </div>
        ) : null}

        {resendNotice ? (
          <p className="rounded-lg border border-teal-200 bg-white px-3 py-2 text-xs text-teal-900">
            {resendNotice}
          </p>
        ) : null}

        <div className="flex flex-wrap items-center gap-3 pt-1">
          <Link
            href={backLoginPath}
            className="inline-flex rounded-xl bg-teal-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-teal-800"
          >
            Back to sign in
          </Link>
          <button
            type="button"
            disabled={resendCooldown > 0 || resending}
            onClick={() => {
              void handleResend();
            }}
            className="inline-flex items-center gap-1.5 rounded-xl border border-teal-300 bg-white px-3.5 py-2 text-xs font-semibold text-teal-900 transition hover:bg-teal-100/60 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${resending ? "animate-spin" : ""}`}
              aria-hidden="true"
            />
            {resending
              ? "Sending..."
              : resendCooldown > 0
                ? `Resend in ${resendCooldown}s`
                : "Send link again"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <form
      onSubmit={(e) => {
        void handleSubmit(onSubmit)(e);
      }}
      noValidate
      className="space-y-4"
    >
      {serverError ? (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-900"
        >
          <AlertCircle
            className="mt-0.5 h-4 w-4 shrink-0 text-rose-600"
            aria-hidden="true"
          />
          <span>{serverError}</span>
        </div>
      ) : null}

      <div>
        <label
          htmlFor="reset-email"
          className="block text-sm font-medium text-slate-800"
        >
          Account email
        </label>
        <input
          id="reset-email"
          type="email"
          autoComplete="email"
          {...register("email")}
          className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-base text-slate-900 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none sm:text-sm"
          placeholder="you@university.edu"
        />
        {errors.email ? (
          <p className="mt-1 text-xs text-rose-600">{errors.email.message}</p>
        ) : null}
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#0b1221] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Sending reset link...
          </>
        ) : (
          "Send password reset link"
        )}
      </button>

      <p className="text-center text-sm text-slate-600">
        Remembered your password?{" "}
        <Link
          href={backLoginPath}
          className="font-semibold text-indigo-700 hover:underline"
        >
          Back to sign in
        </Link>
      </p>
    </form>
  );
}
