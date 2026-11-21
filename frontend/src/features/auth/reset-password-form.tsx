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
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { PORTAL_LABELS, PORTAL_LOGIN_PATHS } from "@/lib/auth/roles";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import type { RoleName } from "@/types/identity";

const resetSchema = z
  .object({
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

type ResetValues = z.infer<typeof resetSchema>;

interface ResetPasswordFormProps {
  portal?: RoleName;
}

export function ResetPasswordForm({ portal }: ResetPasswordFormProps) {
  const [serverError, setServerError] = useState<string | null>(null);
  const [updated, setUpdated] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const loginHref = portal ? PORTAL_LOGIN_PATHS[portal] : "/login";
  const loginLabel = portal
    ? `Continue to ${PORTAL_LABELS[portal]} Login`
    : "Continue to Login";

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetValues>({
    resolver: zodResolver(resetSchema),
    defaultValues: { password: "", confirm_password: "" },
  });

  const passwordValue = useWatch({ control, name: "password" }) || "";
  const rules = [
    { label: "At least 8 characters", met: passwordValue.length >= 8 },
    { label: "Contains a letter", met: /[A-Za-z]/.test(passwordValue) },
    { label: "Contains a number", met: /\d/.test(passwordValue) },
  ];

  async function onSubmit(values: ResetValues) {
    setServerError(null);
    try {
      const supabase = createSupabaseBrowserClient();
      const { error } = await supabase.auth.updateUser({
        password: values.password,
      });
      if (error) {
        setServerError(
          error.message ||
            "Your recovery session may have expired. Please request a new reset link.",
        );
        return;
      }
      await supabase.auth.signOut();
      setUpdated(true);
    } catch (err) {
      setServerError(
        err instanceof Error
          ? err.message
          : "Unable to update your password right now.",
      );
    }
  }

  if (updated) {
    return (
      <div className="space-y-4 rounded-2xl border border-teal-200 bg-teal-50/80 p-6 text-base text-teal-950">
        <div className="flex items-center gap-2.5 font-bold">
          <CheckCircle2 className="h-5 w-5 text-teal-700" aria-hidden="true" />
          <span>Password updated successfully</span>
        </div>
        <p className="text-sm leading-relaxed text-slate-700 sm:text-base">
          Your new password is now active. Sign in through your authorized
          portal to access your workspace.
        </p>
        <Link
          href={loginHref}
          className="inline-flex items-center gap-2 rounded-xl bg-[#0b1221] px-5 py-3 text-[15px] font-semibold text-white transition hover:bg-slate-800"
        >
          <span>{loginLabel}</span>
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
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
      className="space-y-5"
    >
      {serverError ? (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"
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
          htmlFor="new-password"
          className="block text-[15px] font-medium text-slate-800"
        >
          New password
        </label>
        <div className="relative mt-1.5">
          <input
            id="new-password"
            type={showPassword ? "text" : "password"}
            autoComplete="new-password"
            {...register("password")}
            className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-4 pr-11 text-base text-slate-900 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none"
            placeholder="At least 8 characters with letters & numbers"
          />
          <button
            type="button"
            onClick={() => setShowPassword((prev) => !prev)}
            aria-label="Toggle visibility"
            aria-pressed={showPassword}
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
          <p className="mt-1 text-sm text-rose-600">
            {errors.password.message}
          </p>
        ) : null}
        <ul className="mt-2.5 grid grid-cols-1 gap-1.5 text-xs sm:grid-cols-3">
          {rules.map((rule) => (
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
          htmlFor="confirm-new-password"
          className="block text-[15px] font-medium text-slate-800"
        >
          Confirm new password
        </label>
        <div className="relative mt-1.5">
          <input
            id="confirm-new-password"
            type={showConfirm ? "text" : "password"}
            autoComplete="new-password"
            {...register("confirm_password")}
            className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-4 pr-11 text-base text-slate-900 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none"
            placeholder="Re-enter your new password"
          />
          <button
            type="button"
            onClick={() => setShowConfirm((prev) => !prev)}
            aria-label="Toggle confirm field visibility"
            aria-pressed={showConfirm}
            className="absolute inset-y-0 right-0 inline-flex items-center px-3 text-slate-500 transition hover:text-slate-800"
          >
            {showConfirm ? (
              <EyeOff className="h-4 w-4" aria-hidden="true" />
            ) : (
              <Eye className="h-4 w-4" aria-hidden="true" />
            )}
          </button>
        </div>
        {errors.confirm_password ? (
          <p className="mt-1 text-sm text-rose-600">
            {errors.confirm_password.message}
          </p>
        ) : null}
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#0b1221] px-5 py-3.5 text-base font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Updating password...
          </>
        ) : (
          "Save New Password"
        )}
      </button>

      <p className="text-center text-sm text-slate-600">
        Need a fresh recovery email?{" "}
        <Link
          href={portal ? `/forgot-password?portal=${portal}` : "/forgot-password"}
          className="font-semibold text-indigo-700 hover:underline"
        >
          Request reset link again
        </Link>
      </p>
    </form>
  );
}
