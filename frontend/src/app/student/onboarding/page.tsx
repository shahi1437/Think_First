import {
  CheckCircle2,
  Code2,
  Compass,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { OnboardingForm } from "@/features/onboarding/onboarding-form";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

const onboardingBenefits = [
  {
    icon: Compass,
    title: "Learn at your own pace",
    description:
      "Follow lessons and daily goals matched to your schedule and experience.",
  },
  {
    icon: Code2,
    title: "Practice with real coding challenges",
    description:
      "Write Python code, test your solutions, and understand mistakes clearly.",
  },
  {
    icon: TrendingUp,
    title: "Track your progress as you improve",
    description:
      "See which Python skills you have mastered and what to practice next.",
  },
];

export default async function StudentOnboardingPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/onboarding",
  });

  return (
    <div className="mx-auto max-w-6xl py-2 sm:py-4">
      <div className="grid items-start gap-8 lg:grid-cols-12">
        {/* Left Column: Motivational Guidance & Path Preview */}
        <aside className="relative overflow-hidden rounded-3xl border border-slate-800 bg-[#0b1221] p-7 text-white shadow-lg sm:p-9 lg:col-span-5">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(45,212,191,0.18),_transparent_55%),radial-gradient(circle_at_bottom_left,_rgba(79,70,229,0.20),_transparent_60%)]"
          />

          <div className="relative space-y-6">
            {/* Step Progress Indicator */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-teal-300">
                <span className="inline-flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                  Step 1 of 1 · Quick Setup
                </span>
                <span className="text-slate-400">~1 min</span>
              </div>
              <div
                aria-hidden="true"
                className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800"
              >
                <div className="h-full w-full rounded-full bg-gradient-to-r from-teal-400 to-indigo-400" />
              </div>
            </div>

            <div>
              <h1 className="text-3xl font-bold leading-tight tracking-tight text-white sm:text-4xl">
                Let&apos;s Build Your Learning Journey
              </h1>
              <p className="mt-3 text-base leading-relaxed text-slate-300 sm:text-lg">
                Tell us a little about yourself so we can help you start
                learning Python at the right level.
              </p>
            </div>

            <ul className="space-y-4 pt-1">
              {onboardingBenefits.map((benefit) => {
                const Icon = benefit.icon;
                return (
                  <li key={benefit.title} className="flex items-start gap-3.5">
                    <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-400/15 text-teal-300 ring-1 ring-teal-400/30">
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </span>
                    <div>
                      <p className="text-base font-semibold text-white">
                        {benefit.title}
                      </p>
                      <p className="mt-0.5 text-sm leading-relaxed text-slate-300">
                        {benefit.description}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ul>

            {/* Tasteful Visual Journey Card */}
            <div className="rounded-2xl border border-slate-700/80 bg-slate-900/80 p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-teal-300">
                What Happens Next
              </p>
              <div className="mt-3 grid grid-cols-3 gap-2.5 text-center">
                <div className="rounded-xl border border-slate-700/70 bg-slate-800/70 px-2 py-3">
                  <CheckCircle2
                    className="mx-auto h-4 w-4 text-teal-300"
                    aria-hidden="true"
                  />
                  <p className="mt-1.5 text-xs font-semibold text-white">
                    1. Pick Path
                  </p>
                </div>
                <div className="rounded-xl border border-slate-700/70 bg-slate-800/70 px-2 py-3">
                  <Code2
                    className="mx-auto h-4 w-4 text-indigo-300"
                    aria-hidden="true"
                  />
                  <p className="mt-1.5 text-xs font-semibold text-white">
                    2. Practice
                  </p>
                </div>
                <div className="rounded-xl border border-slate-700/70 bg-slate-800/70 px-2 py-3">
                  <TrendingUp
                    className="mx-auto h-4 w-4 text-teal-300"
                    aria-hidden="true"
                  />
                  <p className="mt-1.5 text-xs font-semibold text-white">
                    3. Grow
                  </p>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* Right Column: Spacious Onboarding Form */}
        <div className="lg:col-span-7">
          <OnboardingForm
            mode="onboarding"
            accessToken={accessToken}
            initialUser={user}
          />
        </div>
      </div>
    </div>
  );
}
