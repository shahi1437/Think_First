"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { submitOnboarding, updateUserPreferences } from "@/lib/api-client";
import {
  onboardingFormSchema,
  type OnboardingFormValues,
  type UserMeResponse,
} from "@/types/identity";

interface OnboardingFormProps {
  mode: "onboarding" | "settings";
  accessToken: string;
  initialUser: UserMeResponse;
  onSubmitValues?: (values: OnboardingFormValues) => Promise<UserMeResponse>;
}

export function OnboardingForm({
  mode,
  accessToken,
  initialUser,
  onSubmitValues,
}: OnboardingFormProps) {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const [savedUser, setSavedUser] = useState<UserMeResponse | null>(null);

  const prefs = initialUser.preferences;

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<OnboardingFormValues>({
    resolver: zodResolver(onboardingFormSchema),
    defaultValues: {
      full_name: initialUser.full_name || "",
      programming_experience: prefs?.programming_experience ?? "none",
      preferred_language: prefs?.preferred_language ?? "python",
      learning_goal: prefs?.learning_goal ?? "university_coursework",
      daily_practice_minutes: prefs?.daily_practice_minutes ?? 30,
      preferred_explanation_language:
        prefs?.preferred_explanation_language ?? "en",
      starting_preference: prefs?.starting_preference ?? "guided_beginner",
    },
  });

  async function handleFormSubmit(values: OnboardingFormValues) {
    setServerError(null);
    setSavedUser(null);

    try {
      let updated: UserMeResponse;
      if (onSubmitValues) {
        updated = await onSubmitValues(values);
      } else if (mode === "onboarding") {
        updated = await submitOnboarding(accessToken, values);
      } else {
        updated = await updateUserPreferences(accessToken, {
          programming_experience: values.programming_experience,
          preferred_language: values.preferred_language,
          learning_goal: values.learning_goal,
          daily_practice_minutes: values.daily_practice_minutes,
          preferred_explanation_language: values.preferred_explanation_language,
          starting_preference: values.starting_preference,
        });
      }

      setSavedUser(updated);
      if (mode === "onboarding") {
        router.push("/student");
        router.refresh();
      } else {
        router.refresh();
      }
    } catch (err) {
      setServerError(
        err instanceof Error
          ? err.message
          : "Unable to save your learning preferences.",
      );
    }
  }

  return (
    <form
      onSubmit={(e) => {
        void handleSubmit(handleFormSubmit)(e);
      }}
      noValidate
      className="space-y-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"
    >
      <div className="rounded-lg border border-indigo-100 bg-indigo-50/70 p-4 text-sm text-indigo-950">
        <p className="font-medium">Placement uses evidence, not guesswork.</p>
        <p className="mt-1 text-xs leading-relaxed text-indigo-900">
          Your selections recommend an initial starting track and study schedule.
          Topic-level competency will be updated strictly from your real coding,
          debugging, and verification performance.
        </p>
      </div>

      {serverError ? (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-lg border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-900"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" aria-hidden="true" />
          <span>{serverError}</span>
        </div>
      ) : null}

      {savedUser?.preferences ? (
        <div
          role="status"
          className="flex items-start gap-2.5 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950"
        >
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" aria-hidden="true" />
          <div>
            <p className="font-semibold">Preferences saved</p>
            <p className="mt-1 text-xs text-emerald-900">
              Recommended entry track:{" "}
              <span className="font-mono font-semibold">
                {savedUser.preferences.recommended_entry_track}
              </span>
              . {savedUser.preferences.recommendation_rationale}
            </p>
          </div>
        </div>
      ) : null}

      <div className="grid gap-5 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label
            htmlFor="onboard-full-name"
            className="block text-sm font-medium text-slate-800"
          >
            Full name
          </label>
          <input
            id="onboard-full-name"
            type="text"
            disabled={mode === "settings"}
            {...register("full_name")}
            className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 disabled:bg-slate-100 disabled:text-slate-600"
            placeholder="Your full name"
          />
          {errors.full_name ? (
            <p className="mt-1 text-xs text-rose-600">{errors.full_name.message}</p>
          ) : null}
        </div>

        <div>
          <label
            htmlFor="onboard-experience"
            className="block text-sm font-medium text-slate-800"
          >
            Programming experience
          </label>
          <select
            id="onboard-experience"
            {...register("programming_experience")}
            className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900"
          >
            <option value="none">Absolute Beginner (No prior coding)</option>
            <option value="beginner">Beginner (Basic syntax / school level)</option>
            <option value="basic">Basic (University CS/SWE/IT fundamentals)</option>
            <option value="intermediate">Intermediate (Comfortable writing programs)</option>
            <option value="advanced">Advanced (Strong algorithms &amp; engineering)</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="onboard-language"
            className="block text-sm font-medium text-slate-800"
          >
            Preferred programming language
          </label>
          <select
            id="onboard-language"
            {...register("preferred_language")}
            className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900"
          >
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="cpp">C++</option>
            <option value="java">Java</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="onboard-goal"
            className="block text-sm font-medium text-slate-800"
          >
            Primary learning goal
          </label>
          <select
            id="onboard-goal"
            {...register("learning_goal")}
            className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900"
          >
            <option value="school_fundamentals">School programming fundamentals</option>
            <option value="university_coursework">University CSE/SWE/IT coursework</option>
            <option value="debugging_mastery">Independent debugging mastery</option>
            <option value="interview_prep">Technical interview preparation</option>
            <option value="competitive_programming">Algorithmic problem solving</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="onboard-minutes"
            className="block text-sm font-medium text-slate-800"
          >
            Available daily practice time (minutes)
          </label>
          <input
            id="onboard-minutes"
            type="number"
            min={10}
            max={240}
            step={5}
            {...register("daily_practice_minutes", { valueAsNumber: true })}
            className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900"
          />
          {errors.daily_practice_minutes ? (
            <p className="mt-1 text-xs text-rose-600">
              {errors.daily_practice_minutes.message}
            </p>
          ) : null}
        </div>

        <div>
          <label
            htmlFor="onboard-explanation-lang"
            className="block text-sm font-medium text-slate-800"
          >
            Preferred explanation language
          </label>
          <select
            id="onboard-explanation-lang"
            {...register("preferred_explanation_language")}
            className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900"
          >
            <option value="en">English</option>
            <option value="bn">Bangla (বাংলা)</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="onboard-start-pref"
            className="block text-sm font-medium text-slate-800"
          >
            Preferred starting path
          </label>
          <select
            id="onboard-start-pref"
            {...register("starting_preference")}
            className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900"
          >
            <option value="guided_beginner">
              Start with guided foundation lessons
            </option>
            <option value="diagnostic_assessment">
              Take the 8-area diagnostic skill assessment
            </option>
          </select>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Saving...
            </>
          ) : mode === "onboarding" ? (
            "Complete onboarding"
          ) : (
            "Save preferences"
          )}
        </button>
      </div>
    </form>
  );
}
