import { OnboardingForm } from "@/features/onboarding/onboarding-form";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export default async function StudentOnboardingPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/onboarding",
  });

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-teal-700">
          Smart Onboarding
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">
          Personalize your CodeMentor AI starting path
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Tell us about your current background, preferred language, and daily
          practice time so we can recommend the right starting track.
        </p>
      </div>

      <OnboardingForm
        mode="onboarding"
        accessToken={accessToken}
        initialUser={user}
      />
    </div>
  );
}
