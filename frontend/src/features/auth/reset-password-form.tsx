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
  RefreshCw,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import {
  broadcastLogoutEvent,
  clearClientAuthCaches,
  mapAuthPageError,
} from "@/lib/auth/auth-helpers";
import { PORTAL_LABELS, PORTAL_LOGIN_PATHS } from "@/lib/auth/roles";
import { isSupabaseConfigured } from "@/lib/env";
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
type RecoveryState = "checking" | "ready" | "invalid" | "updated";

interface ResetPasswordFormProps {
  portal?: RoleName;
  initialErrorCode?: string;
}

function stripSensitiveUrlParams(portal?: RoleName): void {
  if (typeof window === "undefined") return;
  try {
    const cleanPath = portal
      ? `/reset-password?portal=${encodeURIComponent(portal)}`
      : "/reset-password";
    window.history.replaceState(null, "", cleanPath);
  } catch {
    // Ignore history API restrictions
  }
}

export function ResetPasswordForm({
  portal,
  initialErrorCode,
}: ResetPasswordFormProps) {
  const configured = isSupabaseConfigured();
  const [recoveryState, setRecoveryState] = useState<RecoveryState>(() =>
    initialErrorCode || !configured ? "invalid" : "checking",
  );
  const [recoveryError, setRecoveryError] = useState<string | null>(() => {
    if (initialErrorCode) {
      return (
        mapAuthPageError(initialErrorCode) ??
        "Your password recovery link is invalid, expired, or has already been used. Please request a fresh reset link."
      );
    }
    if (!configured) {
      return mapAuthPageError("supabase_unconfigured") ?? null;
    }
    return null;
  });
  const [serverError, setServerError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const loginHref = portal ? PORTAL_LOGIN_PATHS[portal] : "/login";
  const forgotHref = portal
    ? `/forgot-password?portal=${portal}`
    : "/forgot-password";
  const loginLabel = portal
    ? `Continue to ${PORTAL_LABELS[portal]} Login`
    : "Continue to Login";

  useEffect(() => {
    if (initialErrorCode || !configured) {
      return;
    }

    let cancelled = false;
    const supabase = createSupabaseBrowserClient();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (cancelled) return;
      if (
        (event === "PASSWORD_RECOVERY" || event === "SIGNED_IN") &&
        session
      ) {
        stripSensitiveUrlParams(portal);
        setRecoveryError(null);
        setRecoveryState("ready");
      }
    });

    async function verifyRecoverySession() {
      try {
        const searchParams = new URLSearchParams(window.location.search);
        const hashRaw = window.location.hash.startsWith("#")
          ? window.location.hash.slice(1)
          : "";
        const hashParams = new URLSearchParams(hashRaw);

        const urlError =
          searchParams.get("error") ||
          searchParams.get("error_code") ||
          hashParams.get("error") ||
          hashParams.get("error_code");
        if (urlError) {
          stripSensitiveUrlParams(portal);
          if (!cancelled) {
            setRecoveryError(
              mapAuthPageError("recovery_expired") ??
                "Your password recovery link is invalid or expired.",
            );
            setRecoveryState("invalid");
          }
          return;
        }

        // 1. Cross-device / mobile OTP token_hash landing directly on /reset-password
        const tokenHash = searchParams.get("token_hash");
        const queryType = searchParams.get("type");
        if (tokenHash && (!queryType || queryType === "recovery")) {
          const { error } = await supabase.auth.verifyOtp({
            token_hash: tokenHash,
            type: "recovery",
          });
          stripSensitiveUrlParams(portal);
          if (cancelled) return;
          if (error) {
            setRecoveryError(
              mapAuthPageError("recovery_expired") ?? error.message,
            );
            setRecoveryState("invalid");
            return;
          }
          setRecoveryState("ready");
          return;
        }

        // 2. PKCE code landing directly on /reset-password
        const code = searchParams.get("code");
        if (code) {
          const { error } = await supabase.auth.exchangeCodeForSession(code);
          stripSensitiveUrlParams(portal);
          if (cancelled) return;
          if (error) {
            setRecoveryError(
              mapAuthPageError("recovery_expired") ?? error.message,
            );
            setRecoveryState("invalid");
            return;
          }
          setRecoveryState("ready");
          return;
        }

        // 3. Implicit/hash recovery tokens (#access_token=...&refresh_token=...&type=recovery)
        const accessToken = hashParams.get("access_token");
        const refreshToken = hashParams.get("refresh_token");
        if (accessToken && refreshToken) {
          const { error } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });
          stripSensitiveUrlParams(portal);
          if (cancelled) return;
          if (error) {
            setRecoveryError(
              mapAuthPageError("recovery_expired") ?? error.message,
            );
            setRecoveryState("invalid");
            return;
          }
          setRecoveryState("ready");
          return;
        }

        // 4. Existing recovery session established by /auth/callback (also supports browser refresh!)
        const {
          data: { user },
          error: userError,
        } = await supabase.auth.getUser();
        if (cancelled) return;
        if (!userError && user) {
          setRecoveryState("ready");
          return;
        }

        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (cancelled) return;
        if (session?.access_token) {
          setRecoveryState("ready");
          return;
        }

        setRecoveryError(
          mapAuthPageError("recovery_missing") ??
            "No active password recovery session was found. Please request a fresh reset link.",
        );
        setRecoveryState("invalid");
      } catch {
        if (!cancelled) {
          setRecoveryError(
            "Unable to verify your password recovery link right now. Please request a fresh reset link and try again.",
          );
          setRecoveryState("invalid");
        }
      }
    }

    void verifyRecoverySession();

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, [configured, initialErrorCode, portal]);

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
        const normalized = error.message.toLowerCase();
        if (
          normalized.includes("auth session missing") ||
          normalized.includes("session_not_found") ||
          normalized.includes("jwt expired") ||
          normalized.includes("invalid jwt")
        ) {
          setRecoveryError(
            mapAuthPageError("recovery_expired") ??
              "Your recovery session has expired. Please request a new reset link.",
          );
          setRecoveryState("invalid");
          return;
        }
        if (normalized.includes("different from the old password")) {
          setServerError(
            "Your new password must be different from your previous password.",
          );
          return;
        }
        setServerError(
          error.message ||
            "Your recovery session may have expired. Please request a new reset link.",
        );
        return;
      }

      try {
        await supabase.auth.signOut({ scope: "global" });
      } catch {
        await supabase.auth.signOut();
      }
      clearClientAuthCaches();
      broadcastLogoutEvent();
      setRecoveryState("updated");
    } catch (err) {
      setServerError(
        err instanceof Error
          ? err.message
          : "Unable to update your password right now.",
      );
    }
  }

  if (recoveryState === "checking") {
    return (
      <div
        role="status"
        className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-6 py-10 text-center"
      >
        <Loader2
          className="h-6 w-6 animate-spin text-indigo-600"
          aria-hidden="true"
        />
        <p className="text-sm font-semibold text-slate-800">
          Verifying your recovery link...
        </p>
        <p className="text-xs text-slate-500">
          Confirming your secure password reset session.
        </p>
      </div>
    );
  }

  if (recoveryState === "invalid") {
    return (
      <div className="space-y-4 rounded-2xl border border-rose-200 bg-rose-50/80 p-6 text-slate-900">
        <div role="alert" className="flex items-start gap-2.5">
          <AlertCircle
            className="mt-0.5 h-5 w-5 shrink-0 text-rose-600"
            aria-hidden="true"
          />
          <div className="space-y-1.5">
            <p className="font-bold text-rose-950">
              Password recovery link unavailable
            </p>
            <p className="text-sm leading-relaxed text-rose-900">
              {recoveryError ??
                "Your password recovery link is invalid, expired, or has already been used. Please request a fresh link."}
            </p>
          </div>
        </div>

        <p className="rounded-xl border border-rose-200/80 bg-white/80 px-3.5 py-2.5 text-xs leading-relaxed text-slate-700">
          Password reset links are single-use and time-limited. If you opened an
          older email or switched devices/browsers mid-recovery, request a new
          link below and open it right away.
        </p>

        <div className="flex flex-wrap items-center gap-3 pt-1">
          <Link
            href={forgotHref}
            className="inline-flex items-center gap-2 rounded-xl bg-[#0b1221] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            <span>Request a New Reset Link</span>
          </Link>
          <Link
            href={loginHref}
            className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            Back to Login
          </Link>
        </div>
      </div>
    );
  }

  if (recoveryState === "updated") {
    return (
      <div className="space-y-4 rounded-2xl border border-teal-200 bg-teal-50/80 p-6 text-base text-teal-950">
        <div className="flex items-center gap-2.5 font-bold">
          <CheckCircle2 className="h-5 w-5 text-teal-700" aria-hidden="true" />
          <span>Password updated successfully</span>
        </div>
        <p className="text-sm leading-relaxed text-slate-700 sm:text-base">
          Your new password is now active and previous sessions have been signed
          out. Sign in through your authorized portal to access your workspace.
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
          href={forgotHref}
          className="font-semibold text-indigo-700 hover:underline"
        >
          Request reset link again
        </Link>
      </p>
    </form>
  );
}
