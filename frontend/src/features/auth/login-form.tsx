"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { fetchCurrentUser } from "@/lib/api-client";
import { resolvePostLoginRedirect } from "@/lib/auth/roles";
import { isSupabaseConfigured } from "@/lib/env";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import type { RoleName } from "@/types/identity";

const loginSchema = z.object({
  email: z.email("Please enter a valid email address."),
  password: z.string().min(8, "Password must be at least 8 characters."),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

interface LoginFormProps {
  nextPath?: string;
  initialError?: string;
  onAuthenticate?: (values: LoginFormValues) => Promise<RoleName[] | void>;
}

export function LoginForm({
  nextPath,
  initialError,
  onAuthenticate,
}: LoginFormProps) {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(
    initialError ?? null,
  );
  const configured = isSupabaseConfigured();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: LoginFormValues) {
    setServerError(null);
    try {
      if (onAuthenticate) {
        const resultRoles = await onAuthenticate(values);
        const resolvedRoles: RoleName[] =
          Array.isArray(resultRoles) && resultRoles.length > 0
            ? resultRoles
            : ["student"];
        router.push(resolvePostLoginRedirect(resolvedRoles, nextPath));
        router.refresh();
        return;
      }

      const supabase = createSupabaseBrowserClient();
      const { error } = await supabase.auth.signInWithPassword({
        email: values.email.trim().toLowerCase(),
        password: values.password,
      });

      if (error) {
        setServerError(error.message);
        return;
      }

      let roles: RoleName[] = ["student"];
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session?.access_token) {
        try {
          const user = await fetchCurrentUser(session.access_token);
          if (user.roles.length > 0) {
            roles = user.roles;
          }
        } catch {
          roles = ["student"];
        }
      }

      router.push(resolvePostLoginRedirect(roles, nextPath));
      router.refresh();
    } catch (err) {
      setServerError(
        err instanceof Error ? err.message : "Unable to sign in right now.",
      );
    }
  }

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
          className="flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50 p-3.5 text-sm text-amber-900"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" aria-hidden="true" />
          <span>
            Supabase environment variables are not configured yet. Configure{" "}
            <code className="font-mono text-xs">NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
            <code className="font-mono text-xs">NEXT_PUBLIC_SUPABASE_ANON_KEY</code>{" "}
            in <code className="font-mono text-xs">frontend/.env.local</code> to sign in.
          </span>
        </div>
      ) : null}

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
          className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none"
          placeholder="student@university.edu"
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
            href="/forgot-password"
            className="text-xs font-medium text-indigo-700 hover:underline"
          >
            Forgot password?
          </Link>
        </div>
        <input
          id="login-password"
          type="password"
          autoComplete="current-password"
          {...register("password")}
          className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-600 focus:outline-none"
          placeholder="Enter your password"
        />
        {errors.password ? (
          <p className="mt-1 text-xs text-rose-600">{errors.password.message}</p>
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
            Signing in...
          </>
        ) : (
          "Sign in"
        )}
      </button>

      <p className="text-center text-sm text-slate-600">
        New to CodeMentor AI?{" "}
        <Link href="/register" className="font-medium text-indigo-700 hover:underline">
          Create a student account
        </Link>
      </p>
    </form>
  );
}
