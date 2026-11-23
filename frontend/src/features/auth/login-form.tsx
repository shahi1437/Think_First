"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Eye, EyeOff, Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import {
  ApiClientError,
  BackendUnavailableError,
  fetchCurrentUser,
  verifyLoginPortal,
} from "@/lib/api-client";
import {
  buildAuthCallbackUrl,
  clearClientAuthCaches,
} from "@/lib/auth/auth-helpers";
import {
  getPortalMismatchMessage,
  isAuthorizedForLoginPortal,
  PORTAL_LABELS,
  PORTAL_LOGIN_PATHS,
  PORTAL_PATHS,
  resolvePostLoginRedirect,
} from "@/lib/auth/roles";
import { isSupabaseConfigured } from "@/lib/env";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import type { RoleName } from "@/types/identity";

const loginSchema = z.object({
  email: z.email("Please enter a valid email address."),
  password: z.string().min(8, "Password must be at least 8 characters."),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

interface LoginFormProps {
  portal?: RoleName;
  nextPath?: string;
  initialError?: string;
  initialSuggestedPortal?: RoleName;
  onAuthenticate?: (values: LoginFormValues) => Promise<RoleName[] | void>;
}

const MAX_FAILED_ATTEMPTS = 5;
const COOLDOWN_SECONDS = 30;

function pickSuggestedPortal(roles: readonly RoleName[]): RoleName | null {
  if (roles.includes("admin")) return "admin";
  if (roles.includes("teacher")) return "teacher";
  if (roles.includes("student")) return "student";
  return null;
}

export function formatAuthError(rawMessage: string, portal?: RoleName): string {
  const normalized = rawMessage.toLowerCase();
  if (
    normalized.includes("invalid login credentials") ||
    normalized.includes("invalid_credentials")
  ) {
    if (portal === "teacher" || portal === "admin") {
      const label = PORTAL_LABELS[portal];
      return `Invalid email or password for this environment. Double-check your credentials or use "Forgot password?" below. If your ${label} account has not been provisioned on this server yet, contact an administrator.`;
    }
    return 'Invalid email or password. Please double-check your credentials, or use "Forgot password?" to reset your password.';
  }
  if (normalized.includes("email not confirmed")) {
    return "Your email address is not confirmed yet. Please open the verification link sent to your inbox before signing in, or resend the confirmation email below.";
  }
  if (
    normalized.includes("rate limit") ||
    normalized.includes("too many requests") ||
    normalized.includes("429")
  ) {
    return "Too many sign-in attempts were detected. Please wait a minute before trying again.";
  }
  if (
    normalized.includes("failed to fetch") ||
    normalized.includes("network") ||
    normalized.includes("cors")
  ) {
    return "Unable to reach the authentication service. Please check your connection and try again.";
  }
  return rawMessage;
}

export function LoginForm({
  portal,
  nextPath,
  initialError,
  initialSuggestedPortal,
  onAuthenticate,
}: LoginFormProps) {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(
    initialError ?? null,
  );
  const [suggestedPortal, setSuggestedPortal] = useState<RoleName | null>(
    initialSuggestedPortal ?? null,
  );
  const [unconfirmedEmail, setUnconfirmedEmail] = useState<string | null>(null);
  const [resendingConfirmation, setResendingConfirmation] = useState(false);
  const [resendFeedback, setResendFeedback] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [failedAttempts, setFailedAttempts] = useState(0);
  const [cooldownUntil, setCooldownUntil] = useState<number | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const configured = isSupabaseConfigured();

  useEffect(() => {
    if (!cooldownUntil) return;
    const updateRemaining = () => {
      const remaining = Math.max(
        0,
        Math.ceil((cooldownUntil - Date.now()) / 1000),
      );
      setSecondsLeft(remaining);
      if (remaining === 0) {
        setCooldownUntil(null);
        setFailedAttempts(0);
      }
    };
    updateRemaining();
    const timer = window.setInterval(updateRemaining, 1000);
    return () => window.clearInterval(timer);
  }, [cooldownUntil]);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  function recordFailedAttempt() {
    const nextCount = failedAttempts + 1;
    setFailedAttempts(nextCount);
    if (nextCount >= MAX_FAILED_ATTEMPTS) {
      setCooldownUntil(Date.now() + COOLDOWN_SECONDS * 1000);
    }
  }

  async function handleResendConfirmation() {
    if (!unconfirmedEmail || resendingConfirmation) return;
    setResendingConfirmation(true);
    setResendFeedback(null);
    try {
      const supabase = createSupabaseBrowserClient();
      const { error } = await supabase.auth.resend({
        type: "signup",
        email: unconfirmedEmail,
        options: {
          emailRedirectTo: buildAuthCallbackUrl("/student/onboarding"),
        },
      });
      if (error) {
        setResendFeedback(formatAuthError(error.message, portal));
      } else {
        setResendFeedback(
          "A new confirmation email has been requested. Please check your inbox and spam folder.",
        );
      }
    } catch {
      setResendFeedback("Could not resend the confirmation email right now.");
    } finally {
      setResendingConfirmation(false);
    }
  }

  async function onSubmit(values: LoginFormValues) {
    if (cooldownUntil && Date.now() < cooldownUntil) {
      setServerError(
        `Too many sign-in attempts. Please wait ${secondsLeft} seconds before trying again.`,
      );
      return;
    }

    setServerError(null);
    setSuggestedPortal(null);
    setUnconfirmedEmail(null);
    setResendFeedback(null);

    try {
      if (onAuthenticate) {
        const resultRoles = await onAuthenticate(values);
        const resolvedRoles: RoleName[] =
          Array.isArray(resultRoles) && resultRoles.length > 0
            ? resultRoles
            : ["student"];
        if (portal && !isAuthorizedForLoginPortal(resolvedRoles, portal)) {
          recordFailedAttempt();
          setServerError(getPortalMismatchMessage(portal, resolvedRoles));
          setSuggestedPortal(pickSuggestedPortal(resolvedRoles));
          return;
        }
        setFailedAttempts(0);
        const target = portal
          ? resolvePostLoginRedirect(
              resolvedRoles,
              nextPath ?? PORTAL_PATHS[portal],
            )
          : resolvePostLoginRedirect(resolvedRoles, nextPath);
        router.push(target);
        router.refresh();
        return;
      }

      const normalizedEmail = values.email.trim().toLowerCase();
      const supabase = createSupabaseBrowserClient();
      const { error } = await supabase.auth.signInWithPassword({
        email: normalizedEmail,
        password: values.password,
      });

      if (error) {
        recordFailedAttempt();
        if (error.message.toLowerCase().includes("email not confirmed")) {
          setUnconfirmedEmail(normalizedEmail);
        }
        setServerError(formatAuthError(error.message, portal));
        return;
      }

      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session?.access_token) {
        await supabase.auth.signOut();
        setServerError(
          "Your session could not be initialized. Please verify your email and try again.",
        );
        return;
      }

      try {
        const user = portal
          ? await verifyLoginPortal(session.access_token, portal)
          : await fetchCurrentUser(session.access_token);

        if (user.roles.length === 0) {
          await supabase.auth.signOut();
          setServerError(
            "Your credentials were accepted, but no authorized role is assigned to this account yet. Please contact an administrator.",
          );
          return;
        }

        if (portal && !isAuthorizedForLoginPortal(user.roles, portal)) {
          await supabase.auth.signOut();
          recordFailedAttempt();
          setServerError(getPortalMismatchMessage(portal, user.roles));
          setSuggestedPortal(pickSuggestedPortal(user.roles));
          return;
        }

        setFailedAttempts(0);
        clearClientAuthCaches();
        const target = portal
          ? resolvePostLoginRedirect(
              user.roles,
              nextPath ?? PORTAL_PATHS[portal],
            )
          : resolvePostLoginRedirect(user.roles, nextPath);
        router.push(target);
        router.refresh();
      } catch (verifyErr) {
        if (
          verifyErr instanceof ApiClientError &&
          verifyErr.status === 403 &&
          portal
        ) {
          let discoveredPortal: RoleName | null = null;
          let hasNoRoles = false;
          try {
            const actualUser = await fetchCurrentUser(session.access_token);
            if (actualUser.roles.length === 0) {
              hasNoRoles = true;
            } else {
              discoveredPortal = pickSuggestedPortal(actualUser.roles);
            }
          } catch {
            // Fall back cleanly to the backend denial message
          } finally {
            await supabase.auth.signOut();
          }

          recordFailedAttempt();
          if (hasNoRoles) {
            setServerError(
              "Your password was accepted, but no authorized role is assigned to this account yet. Please contact an administrator.",
            );
            return;
          }
          if (discoveredPortal) {
            setSuggestedPortal(discoveredPortal);
          }
          setServerError(
            `Your password was accepted, but this account does not have ${PORTAL_LABELS[portal]} portal access. Please sign in through your authorized login portal.`,
          );
          return;
        }

        await supabase.auth.signOut();

        if (verifyErr instanceof ApiClientError && verifyErr.status === 401) {
          setServerError(
            "Your sign-in session could not be verified by the learning server (invalid or expired authentication token). Please try signing in again.",
          );
          return;
        }

        if (verifyErr instanceof ApiClientError && verifyErr.status === 403) {
          recordFailedAttempt();
          setServerError(verifyErr.message);
          return;
        }

        if (verifyErr instanceof BackendUnavailableError) {
          setServerError(
            "Unable to verify your account permissions because the learning server is temporarily unreachable. Please try again in a moment.",
          );
          return;
        }
        setServerError(
          verifyErr instanceof Error
            ? verifyErr.message
            : "Unable to verify your account permissions right now.",
        );
      }
    } catch (err) {
      recordFailedAttempt();
      setServerError(
        err instanceof Error
          ? formatAuthError(err.message, portal)
          : "Unable to sign in right now.",
      );
    }
  }

  const emailPlaceholder =
    portal === "admin"
      ? "admin@university.edu"
      : portal === "teacher"
        ? "instructor@university.edu"
        : "student@university.edu";

  const buttonLabel = portal
    ? `Sign in as ${PORTAL_LABELS[portal]}`
    : "Sign in";

  return (
    <form
      onSubmit={(e) => {
        void handleSubmit(onSubmit)(e);
      }}
      noValidate
      className="space-y-5"
    >
      {!configured && !onAuthenticate ? (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-sm text-amber-900"
        >
          <AlertCircle
            className="mt-0.5 h-4 w-4 shrink-0 text-amber-700"
            aria-hidden="true"
          />
          <span>
            Authentication configuration is incomplete for this local
            environment. Please configure Supabase settings before signing in.
          </span>
        </div>
      ) : null}

      {serverError ? (
        <div
          role="alert"
          className="space-y-2 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-900"
        >
          <div className="flex items-start gap-2.5">
            <AlertCircle
              className="mt-0.5 h-4 w-4 shrink-0 text-rose-600"
              aria-hidden="true"
            />
            <span>{serverError}</span>
          </div>
          {suggestedPortal ? (
            <div className="pl-6">
              <Link
                href={PORTAL_LOGIN_PATHS[suggestedPortal]}
                className="text-xs font-semibold text-rose-800 underline hover:text-rose-950"
              >
                Open {PORTAL_LABELS[suggestedPortal]} Login →
              </Link>
            </div>
          ) : null}
          {unconfirmedEmail ? (
            <div className="space-y-1.5 pl-6 pt-1">
              <button
                type="button"
                disabled={resendingConfirmation}
                onClick={() => {
                  void handleResendConfirmation();
                }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-rose-300 bg-white px-3 py-1.5 text-xs font-semibold text-rose-900 transition hover:bg-rose-100/60 disabled:opacity-60"
              >
                <RefreshCw
                  className={`h-3.5 w-3.5 ${resendingConfirmation ? "animate-spin" : ""}`}
                  aria-hidden="true"
                />
                {resendingConfirmation
                  ? "Sending confirmation email..."
                  : "Resend confirmation email"}
              </button>
              {resendFeedback ? (
                <p className="text-xs text-slate-700">{resendFeedback}</p>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      {secondsLeft > 0 ? (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-900">
          Login temporarily paused for {secondsLeft}s due to repeated failed
          attempts.
        </p>
      ) : null}

      <div>
        <label
          htmlFor="login-email"
          className="block text-sm font-medium text-slate-800"
        >
          Email address
        </label>
        <input
          id="login-email"
          type="email"
          autoComplete="email"
          {...register("email")}
          className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-base text-slate-900 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none sm:text-sm"
          placeholder={emailPlaceholder}
        />
        {errors.email ? (
          <p className="mt-1 text-xs text-rose-600">{errors.email.message}</p>
        ) : null}
      </div>

      <div>
        <div className="flex items-center justify-between">
          <label
            htmlFor="login-password"
            className="block text-sm font-medium text-slate-800"
          >
            Password
          </label>
          <Link
            href={
              portal ? `/forgot-password?portal=${portal}` : "/forgot-password"
            }
            className="text-xs font-medium text-indigo-700 hover:underline"
          >
            Forgot password?
          </Link>
        </div>
        <div className="relative mt-1.5">
          <input
            id="login-password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            {...register("password")}
            className="w-full rounded-xl border border-slate-300 bg-white py-3 pl-4 pr-11 text-base text-slate-900 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none sm:text-sm"
            placeholder="Enter your password"
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
      </div>

      <button
        type="submit"
        disabled={isSubmitting || secondsLeft > 0}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#0b1221] px-5 py-3 text-base font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60 sm:text-sm"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Signing in...
          </>
        ) : (
          buttonLabel
        )}
      </button>

      {!portal || portal === "student" ? (
        <p className="text-center text-sm text-slate-600">
          New to Think_First?{" "}
          <Link
            href="/register"
            className="font-semibold text-teal-700 hover:underline"
          >
            Create student account
          </Link>
        </p>
      ) : portal === "teacher" ? (
        <p className="rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs leading-relaxed text-slate-600">
          Teacher accounts are provisioned and approved by an authorized
          platform administrator. Public self-registration is disabled for
          instructor roles.
        </p>
      ) : (
        <p className="rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-xs leading-relaxed text-slate-600">
          Restricted institutional portal. Only accounts with verified Admin
          privileges are permitted to sign in here.
        </p>
      )}
    </form>
  );
}
