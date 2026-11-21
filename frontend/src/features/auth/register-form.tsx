"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCircle2,
  Eye,
  EyeOff,
  Loader2,
  MailCheck,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { publicEnv } from "@/lib/env";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

const registerSchema = z
  .object({
    full_name: z
      .string()
      .trim()
      .min(2, "Full name must be at least 2 characters.")
      .max(120, "Full name must be 120 characters or fewer."),
    email: z.email("Please enter a valid email address."),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters.")
      .max(128, "Password must be 128 characters or fewer.")
      .refine(
        (val) => /[A-Za-z]/.test(val) && /\d/.test(val),
        "Password must include at least one letter and one number.",
      ),
    confirm_password: z.string(),
  })
  .refine((data) => data.password === data.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords do not match.",
  });

type RegisterFormValues = z.infer<typeof registerSchema>;

interface RegistrationResult {
  email: string;
  requiresEmailVerification: boolean;
}

export function RegisterForm() {
  const [serverError, setServerError] = useState<string | null>(null);
  const [result, setResult] = useState<RegistrationResult | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [resending, setResending] = useState(false);
  const [resendMessage, setResendMessage] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: "",
      email: "",
      password: "",
      confirm_password: "",
    },
  });

  const passwordValue = useWatch({ control, name: "password" }) || "";
  const passwordRules = [
    {
      label: "At least 8 characters",
      met: passwordValue.length >= 8,
    },
    {
      label: "Contains a letter",
      met: /[A-Za-z]/.test(passwordValue),
    },
    {
      label: "Contains a number",
      met: /\d/.test(passwordValue),
    },
  ];

  async function onSubmit(values: RegisterFormValues) {
    setServerError(null);
    setResendMessage(null);
    const normalizedEmail = values.email.trim().toLowerCase();

    try {
      const supabase = createSupabaseBrowserClient();
      const { data, error } = await supabase.auth.signUp({
        email: normalizedEmail,
        password: values.password,
        options: {
          emailRedirectTo: `${publicEnv.NEXT_PUBLIC_APP_URL}/auth/callback?next=/student/onboarding`,
          data: {
            full_name: values.full_name.trim(),
          },
        },
      });

      if (error) {
        setServerError(error.message);
        return;
      }

      setResult({
        email: normalizedEmail,
        requiresEmailVerification: !data.session,
      });
    } catch (err) {
      setServerError(
        err instanceof Error ? err.message : "Unable to create account.",
      );
    }
  }

  async function handleResendVerification() {
    if (!result) return;
    setResending(true);
    setResendMessage(null);
    try {
      const supabase = createSupabaseBrowserClient();
      const { error } = await supabase.auth.resend({
        type: "signup",
        email: result.email,
        options: {
          emailRedirectTo: `${publicEnv.NEXT_PUBLIC_APP_URL}/auth/callback?next=/student/onboarding`,
        },
      });
      if (error) {
        setResendMessage(error.message);
      } else {
        setResendMessage(
          "A fresh verification email has been requested. Please check your inbox.",
        );
      }
    } catch {
      setResendMessage("Could not resend the verification email right now.");
    } finally {
      setResending(false);
    }
  }

  if (result) {
    if (result.requiresEmailVerification) {
      return (
        <div className="space-y-5 rounded-2xl border border-teal-200 bg-teal-50/70 p-6 text-slate-900">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white">
              <MailCheck className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-teal-800">
                Verification Required
              </p>
              <h2 className="mt-0.5 text-lg font-bold text-slate-900">
                Verify your email before signing in
              </h2>
            </div>
          </div>

          <p className="text-sm leading-relaxed text-slate-700">
            We created a pending Student registration for{" "}
            <span className="font-semibold text-slate-950">{result.email}</span>
            . Your account is not active until you confirm your email address.
          </p>

          <ol className="space-y-2 rounded-xl border border-teal-200 bg-white p-4 text-xs leading-relaxed text-slate-700">
            <li>
              <strong>1. Open your email inbox</strong> (and check your spam or
              promotions folder if you do not see it within a minute).
            </li>
            <li>
              <strong>2. Click the verification link</strong> inside the email
              from Think_First / CodeMentor AI.
            </li>
            <li>
              <strong>3. Return to Student Login</strong> to sign in and start
              your personalized Python onboarding.
            </li>
          </ol>

          {resendMessage ? (
            <p className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700">
              {resendMessage}
            </p>
          ) : null}

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/login/student"
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-[#0b1221] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
            >
              <span>Go to Student Login</span>
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
            <button
              type="button"
              disabled={resending}
              onClick={() => {
                void handleResendVerification();
              }}
              className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${resending ? "animate-spin" : ""}`}
                aria-hidden="true"
              />
              {resending ? "Sending..." : "Resend email"}
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-5 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-6 text-slate-900">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-600 text-white">
            <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-emerald-800">
              Registration Complete
            </p>
            <h2 className="mt-0.5 text-lg font-bold text-slate-900">
              Student account ready
            </h2>
          </div>
        </div>

        <p className="text-sm leading-relaxed text-slate-700">
          Your Student account for{" "}
          <span className="font-semibold text-slate-950">{result.email}</span>{" "}
          has been created and confirmed. You can continue straight into
          onboarding or sign in from the Student Login portal.
        </p>

        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/student/onboarding"
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-800"
          >
            <span>Continue to Onboarding</span>
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
          <Link
            href="/login/student"
            className="inline-flex items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            Student Login
          </Link>
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
          htmlFor="reg-name"
          className="block text-sm font-medium text-slate-800"
        >
          Full name
        </label>
        <input
          id="reg-name"
          type="text"
          autoComplete="name"
          {...register("full_name")}
          className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-base text-slate-900 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none sm:text-sm"
          placeholder="Amina Rahman"
        />
        {errors.full_name ? (
          <p className="mt-1 text-xs text-rose-600">
            {errors.full_name.message}
          </p>
        ) : null}
      </div>

      <div>
        <label
          htmlFor="reg-email"
          className="block text-sm font-medium text-slate-800"
        >
          Email address
        </label>
        <input
          id="reg-email"
          type="email"
          autoComplete="email"
          {...register("email")}
          className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-base text-slate-900 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none sm:text-sm"
          placeholder="student@university.edu"
        />
        {errors.email ? (
          <p className="mt-1 text-xs text-rose-600">{errors.email.message}</p>
        ) : null}
      </div>

      <div>
        <label
          htmlFor="reg-password"
          className="block text-sm font-medium text-slate-800"
        >
          Password
        </label>
        <div className="relative mt-1.5">
          <input
            id="reg-password"
            type={showPassword ? "text" : "password"}
            autoComplete="new-password"
            {...register("password")}
            className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-4 pr-11 text-base text-slate-900 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none sm:text-sm"
            placeholder="At least 8 characters with letters & numbers"
          />
          <button
            type="button"
            onClick={() => setShowPassword((prev) => !prev)}
            aria-label="Toggle visibility"
            aria-pressed={showPassword}
            title={showPassword ? "Hide password" : "Show password"}
            className="absolute inset-y-0 right-0 inline-flex items-center px-3 text-slate-500 transition hover:text-slate-800"
          >
            {showPassword ? (
              <EyeOff className="h-4 w-4" aria-hidden="true" />
            ) : (
              <Eye className="h-4 w-4" aria-hidden="true" />
            )}
          </button>
        </div>
        {errors.password ? (
          <p className="mt-1 text-xs text-rose-600">
            {errors.password.message}
          </p>
        ) : null}

        <ul className="mt-2 grid grid-cols-1 gap-1 text-xs sm:grid-cols-3">
          {passwordRules.map((rule) => (
            <li
              key={rule.label}
              className={`flex items-center gap-1 ${
                rule.met ? "font-medium text-teal-700" : "text-slate-400"
              }`}
            >
              <Check className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span>{rule.label}</span>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <label
          htmlFor="reg-confirm"
          className="block text-sm font-medium text-slate-800"
        >
          Confirm password
        </label>
        <div className="relative mt-1.5">
          <input
            id="reg-confirm"
            type={showConfirmPassword ? "text" : "password"}
            autoComplete="new-password"
            {...register("confirm_password")}
            className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-4 pr-11 text-base text-slate-900 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none sm:text-sm"
            placeholder="Repeat your password"
          />
          <button
            type="button"
            onClick={() => setShowConfirmPassword((prev) => !prev)}
            aria-label="Toggle confirm field visibility"
            aria-pressed={showConfirmPassword}
            title={
              showConfirmPassword
                ? "Hide confirm password"
                : "Show confirm password"
            }
            className="absolute inset-y-0 right-0 inline-flex items-center px-3 text-slate-500 transition hover:text-slate-800"
          >
            {showConfirmPassword ? (
              <EyeOff className="h-4 w-4" aria-hidden="true" />
            ) : (
              <Eye className="h-4 w-4" aria-hidden="true" />
            )}
          </button>
        </div>
        {errors.confirm_password ? (
          <p className="mt-1 text-xs text-rose-600">
            {errors.confirm_password.message}
          </p>
        ) : null}
      </div>

      <p className="rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs leading-relaxed text-slate-600">
        Self-registration creates a <strong>Student</strong> account only.
        Teacher and Admin roles are provisioned exclusively by authorized
        administrators.
      </p>

      <button
        type="submit"
        disabled={isSubmitting}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#0b1221] px-5 py-3 text-base font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60 sm:text-sm"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Creating student account...
          </>
        ) : (
          "Create Student Account"
        )}
      </button>

      <p className="text-center text-sm text-slate-600">
        Already have a Student account?{" "}
        <Link
          href="/login/student"
          className="font-semibold text-teal-700 hover:underline"
        >
          Sign in
        </Link>
      </p>
    </form>
  );
}
