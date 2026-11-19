"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { publicEnv } from "@/lib/env";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

const recoverySchema = z.object({
  email: z.email("Please enter a valid email address."),
});

type RecoveryValues = z.infer<typeof recoverySchema>;

export function ForgotPasswordForm() {
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RecoveryValues>({
    resolver: zodResolver(recoverySchema),
    defaultValues: { email: "" },
  });

  async function onSubmit(values: RecoveryValues) {
    setServerError(null);
    try {
      const supabase = createSupabaseBrowserClient();
      const { error } = await supabase.auth.resetPasswordForEmail(
        values.email.trim().toLowerCase(),
        {
          redirectTo: `${publicEnv.NEXT_PUBLIC_APP_URL}/auth/callback?next=/student/settings`,
        },
      );
      if (error) {
        setServerError(error.message);
        return;
      }
      setSubmitted(true);
    } catch (err) {
      setServerError(
        err instanceof Error ? err.message : "Unable to request password reset.",
      );
    }
  }

  if (submitted) {
    return (
      <div className="space-y-4 rounded-lg border border-teal-200 bg-teal-50 p-5 text-sm text-teal-950">
        <div className="flex items-center gap-2 font-semibold">
          <CheckCircle2 className="h-5 w-5 text-teal-700" aria-hidden="true" />
          <span>Recovery link requested</span>
        </div>
        <p>
          If an account exists for that email address, a password recovery link
          has been sent.
        </p>
        <Link
          href="/login"
          className="inline-flex rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800"
        >
          Back to sign in
        </Link>
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
          className="flex items-start gap-2.5 rounded-lg border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-900"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" aria-hidden="true" />
          <span>{serverError}</span>
        </div>
      ) : null}

      <div>
        <label htmlFor="reset-email" className="block text-sm font-medium text-slate-800">
          Account email
        </label>
        <input
          id="reset-email"
          type="email"
          autoComplete="email"
          {...register("email")}
          className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 focus:border-indigo-600 focus:outline-none"
          placeholder="student@university.edu"
        />
        {errors.email ? (
          <p className="mt-1 text-xs text-rose-600">{errors.email.message}</p>
        ) : null}
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
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
        <Link href="/login" className="font-medium text-indigo-700 hover:underline">
          Back to sign in
        </Link>
      </p>
    </form>
  );
}
