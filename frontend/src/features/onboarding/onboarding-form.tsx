"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  Loader2,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
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

const inputBaseClass =
  "mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-base text-slate-900 placeholder:text-slate-400 transition focus:border-indigo-600 focus:outline-none disabled:bg-slate-100 disabled:text-slate-600";

const selectBaseClass =
  "mt-2 w-full appearance-none rounded-xl border border-slate-300 bg-white py-3 pl-4 pr-10 text-base text-slate-900 transition focus:border-indigo-600 focus:outline-none";

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
    control,
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

  const selectedExp = useWatch({ control, name: "programming_experience" });
  const selectedStartPref = useWatch({ control, name: "starting_preference" });
  const selectedLang = useWatch({ control, name: "preferred_language" });
  const willRouteToDiagnostic =
    selectedExp !== "none" && selectedStartPref === "diagnostic_assessment";

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
        const nextRoute =
          updated.preferences?.entry_redirect_path ||
          (updated.preferences?.recommended_entry_track ===
          "diagnostic_assessment"
            ? "/student/diagnostic?mode=full&entry=onboarding"
            : "/student");
        router.push(nextRoute);
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
      className="space-y-6 rounded-3xl border border-slate-200 bg-white p-7 shadow-sm sm:p-10"
    >
      <div className="border-b border-slate-100 pb-5">
        <h2 className="text-xl font-bold text-slate-900 sm:text-2xl">
          {mode === "onboarding"
            ? "Personalize Your Study Plan"
            : "Learning Preferences"}
        </h2>
        <p className="mt-1.5 text-sm leading-relaxed text-slate-600 sm:text-base">
          {mode === "onboarding"
            ? "Choose your experience level, goal, and daily pace. You can update these settings anytime later."
            : "Update your target programming language, daily study time, and explanation language."}
        </p>
      </div>

      {serverError ? (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900"
        >
          <AlertCircle
            className="mt-0.5 h-5 w-5 shrink-0 text-rose-600"
            aria-hidden="true"
          />
          <span>{serverError}</span>
        </div>
      ) : null}

      {savedUser?.preferences ? (
        <div
          role="status"
          className="flex items-start gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950"
        >
          <CheckCircle2
            className="mt-0.5 h-5 w-5 shrink-0 text-emerald-700"
            aria-hidden="true"
          />
          <div>
            <p className="font-semibold">Preferences saved</p>
            <p className="mt-1 text-sm text-emerald-900">
              Recommended starting path:{" "}
              <span className="font-mono font-semibold">
                {savedUser.preferences.recommended_entry_track}
              </span>
              . {savedUser.preferences.recommendation_rationale}
            </p>
          </div>
        </div>
      ) : null}

      <div className="grid gap-6 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label
            htmlFor="onboard-full-name"
            className="block text-sm font-semibold text-slate-800 sm:text-[15px]"
          >
            Full name
          </label>
          <input
            id="onboard-full-name"
            type="text"
            disabled={mode === "settings"}
            {...register("full_name")}
            className={inputBaseClass}
            placeholder="Enter your full name"
          />
          <p className="mt-1.5 text-[13px] text-slate-500">
            Displayed on your student dashboard and class rosters.
          </p>
          {errors.full_name ? (
            <p className="mt-1 text-sm font-medium text-rose-600">
              {errors.full_name.message}
            </p>
          ) : null}
        </div>

        <div>
          <label
            htmlFor="onboard-experience"
            className="block text-sm font-semibold text-slate-800 sm:text-[15px]"
          >
            Programming experience
          </label>
          <div className="relative">
            <select
              id="onboard-experience"
              {...register("programming_experience")}
              className={selectBaseClass}
            >
              <option value="none">Absolute Beginner (No prior coding)</option>
              <option value="beginner">
                Beginner (Basic syntax / school level)
              </option>
              <option value="basic">
                Basic (University CS/SWE/IT fundamentals)
              </option>
              <option value="intermediate">
                Intermediate (Comfortable writing programs)
              </option>
              <option value="advanced">
                Advanced (Strong algorithms &amp; engineering)
              </option>
            </select>
            <ChevronDown
              className="pointer-events-none absolute right-3.5 top-1/2 mt-1 h-4 w-4 -translate-y-1/2 text-slate-500"
              aria-hidden="true"
            />
          </div>
          <p className="mt-1.5 text-[13px] text-slate-500">
            Helps us suggest comfortable first lessons.
          </p>
        </div>

        <div>
          <label
            htmlFor="onboard-language"
            className="block text-sm font-semibold text-slate-800 sm:text-[15px]"
          >
            Preferred programming language
          </label>
          <div className="relative">
            <select
              id="onboard-language"
              {...register("preferred_language")}
              className={selectBaseClass}
            >
              <option value="python">Python 3</option>
              <option value="javascript">JavaScript (Node.js)</option>
              <option value="c">C (GCC)</option>
              <option value="cpp">C++ (GCC)</option>
              <option value="java">Java (OpenJDK)</option>
            </select>
            <ChevronDown
              className="pointer-events-none absolute right-3.5 top-1/2 mt-1 h-4 w-4 -translate-y-1/2 text-slate-500"
              aria-hidden="true"
            />
          </div>
          <p className="mt-1.5 text-[13px] text-slate-500">
            Learn any of our 5 languages under one account with independent
            progress per language.
          </p>
        </div>

        <div>
          <label
            htmlFor="onboard-goal"
            className="block text-sm font-semibold text-slate-800 sm:text-[15px]"
          >
            Primary learning goal
          </label>
          <div className="relative">
            <select
              id="onboard-goal"
              {...register("learning_goal")}
              className={selectBaseClass}
            >
              <option value="school_fundamentals">
                School programming fundamentals
              </option>
              <option value="university_coursework">
                University CSE/SWE/IT coursework
              </option>
              <option value="debugging_mastery">
                Independent debugging mastery
              </option>
              <option value="interview_prep">
                Technical interview preparation
              </option>
              <option value="competitive_programming">
                Algorithmic problem solving
              </option>
            </select>
            <ChevronDown
              className="pointer-events-none absolute right-3.5 top-1/2 mt-1 h-4 w-4 -translate-y-1/2 text-slate-500"
              aria-hidden="true"
            />
          </div>
          <p className="mt-1.5 text-[13px] text-slate-500">
            Tailors your recommended practice focus.
          </p>
        </div>

        <div>
          <label
            htmlFor="onboard-minutes"
            className="block text-sm font-semibold text-slate-800 sm:text-[15px]"
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
            className={inputBaseClass}
          />
          <p className="mt-1.5 text-[13px] text-slate-500">
            Choose between 10 and 240 minutes per day.
          </p>
          {errors.daily_practice_minutes ? (
            <p className="mt-1 text-sm font-medium text-rose-600">
              {errors.daily_practice_minutes.message}
            </p>
          ) : null}
        </div>

        <div>
          <label
            htmlFor="onboard-explanation-lang"
            className="block text-sm font-semibold text-slate-800 sm:text-[15px]"
          >
            Preferred explanation language
          </label>
          <div className="relative">
            <select
              id="onboard-explanation-lang"
              {...register("preferred_explanation_language")}
              className={selectBaseClass}
            >
              <option value="en">English</option>
              <option value="bn">Bangla (বাংলা)</option>
            </select>
            <ChevronDown
              className="pointer-events-none absolute right-3.5 top-1/2 mt-1 h-4 w-4 -translate-y-1/2 text-slate-500"
              aria-hidden="true"
            />
          </div>
          <p className="mt-1.5 text-[13px] text-slate-500">
            Lessons and feedback can be read in English or Bangla.
          </p>
        </div>

        <div>
          <label
            htmlFor="onboard-start-pref"
            className="block text-sm font-semibold text-slate-800 sm:text-[15px]"
          >
            Preferred starting path
          </label>
          <div className="relative">
            <select
              id="onboard-start-pref"
              {...register("starting_preference")}
              className={selectBaseClass}
            >
              <option value="guided_beginner">
                Start with guided foundation lessons
              </option>
              <option value="diagnostic_assessment">
                Take the 8-area diagnostic skill check
              </option>
            </select>
            <ChevronDown
              className="pointer-events-none absolute right-3.5 top-1/2 mt-1 h-4 w-4 -translate-y-1/2 text-slate-500"
              aria-hidden="true"
            />
          </div>
          <p className="mt-1.5 text-[13px] text-slate-500">
            Begin step-by-step or check your current skill level first.
          </p>
        </div>
      </div>

      {mode === "onboarding" ? (
        <div
          aria-live="polite"
          className="tf-scale-in rounded-2xl border border-indigo-200/80 bg-indigo-50/60 p-4 text-sm text-indigo-950"
        >
          <p className="font-semibold">
            {willRouteToDiagnostic
              ? "Adaptive Entry Path: Direct to 8-Domain Diagnostic"
              : "Gentle Beginner Entry Path: Guided Foundation Lessons First"}
          </p>
          <p className="mt-1 leading-relaxed text-indigo-900">
            {willRouteToDiagnostic
              ? `Because you have prior experience (${selectedExp}) and chose the skill check, we will open your ${selectedLang.toUpperCase()} adaptive diagnostic right after setup to place you on an evidence-backed track.`
              : `You will start smoothly with introductory ${selectedLang.toUpperCase()} foundation lessons before taking a short 4-question readiness check—no overwhelming advanced test upfront.`}
          </p>
        </div>
      ) : null}

      <div className="border-t border-slate-100 pt-5">
        <button
          type="submit"
          disabled={isSubmitting}
          className="tf-btn-press inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#0b1221] to-indigo-900 px-6 py-3.5 text-base font-semibold text-white shadow-sm transition hover:from-slate-800 hover:to-indigo-800 disabled:cursor-not-allowed disabled:opacity-60 sm:text-[17px]"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
              <span>Saving your plan...</span>
            </>
          ) : mode === "onboarding" ? (
            <>
              <span>Start My Learning Journey</span>
              <ArrowRight className="h-5 w-5" aria-hidden="true" />
            </>
          ) : (
            <span>Save Preferences</span>
          )}
        </button>
      </div>
    </form>
  );
}
