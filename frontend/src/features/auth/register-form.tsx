"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
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
      .max(128, "Password must be 128 characters or fewer."),
    confirm_password: z.string(),
  })
  .refine((data) => data.password === data.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords do not match.",
  });

type RegisterFormValues = z.infer<typeof registerSchema>;

export function RegisterForm() {
  const [serverError, setServerError] = useState<string | null>(null);
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);

  const {
    register,
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

  async function onSubmit(values: RegisterFormValues) {
    setServerError(null);
    try {
      const supabase = createSupabaseBrowserClient();
      const { error } = await supabase.auth.signUp({
        email: values.email.trim().toLowerCase(),
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

      setRegisteredEmail(values.email.trim().toLowerCase());
    } catch (err) {
      setServerError(
        err instanceof Error ? err.message : "Unable to create account.",
      );
    }
  }

  if (registeredEmail) {
    return (
      <div className="space-y-4 rounded-lg border border-emerald-200 bg-emerald-50 p-5 text-sm text-emerald-950">
        <div className="flex items-center gap-2 font-semibold">
          <CheckCircle2 className="h-5 w-5 text-emerald-700" aria-hidden="true" />
          <span>Account created</span>
        </div>
        <p className="leading-relaxed">
          We registered <span className="font-semibold">{registeredEmail}</span> as
          a Student account. Check your inbox (or local Supabase Mailpit) to confirm
          your email, then sign in to begin onboarding.
        </p>
        <Link
          href="/login"
          className="inline-flex rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
        >
          Go to sign in
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
        <label htmlFor="reg-name" className="block text-sm font-medium text-slate-800">
          Full name
        </label>
        <input
          id="reg-name"
          type="text"
          autoComplete="name"
          {...register("full_name")}
          className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 focus:border-indigo-600 focus:outline-none"
          placeholder="Amina Rahman"
        />
        {errors.full_name ? (
          <p className="mt-1 text-xs text-rose-600">{errors.full_name.message}</p>
        ) : null}
      </div>

      <div>
        <label htmlFor="reg-email" className="block text-sm font-medium text-slate-800">
          Email address
        </label>
        <input
          id="reg-email"
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

      <div>
        <label htmlFor="reg-password" className="block text-sm font-medium text-slate-800">
          Password
        </label>
        <input
          id="reg-password"
          type="password"
          autoComplete="new-password"
          {...register("password")}
          className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 focus:border-indigo-600 focus:outline-none"
          placeholder="At least 8 characters"
        />
        {errors.password ? (
          <p className="mt-1 text-xs text-rose-600">{errors.password.message}</p>
        ) : null}
      </div>

      <div>
        <label htmlFor="reg-confirm" className="block text-sm font-medium text-slate-800">
          Confirm password
        </label>
        <input
          id="reg-confirm"
          type="password"
          autoComplete="new-password"
          {...register("confirm_password")}
          className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 focus:border-indigo-600 focus:outline-none"
          placeholder="Repeat your password"
        />
        {errors.confirm_password ? (
          <p className="mt-1 text-xs text-rose-600">
            {errors.confirm_password.message}
          </p>
        ) : null}
      </div>

      <p className="text-xs text-slate-500">
        Self-registration creates a Student account. Teacher and Admin roles are
        assigned exclusively by authorized administrators.
      </p>

      <button
        type="submit"
        disabled={isSubmitting}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Creating account...
          </>
        ) : (
          "Create student account"
        )}
      </button>

      <p className="text-center text-sm text-slate-600">
        Already registered?{" "}
        <Link href="/login" className="font-medium text-indigo-700 hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
