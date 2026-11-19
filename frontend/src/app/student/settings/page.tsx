import { OnboardingForm } from "@/features/onboarding/onboarding-form";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export default async function StudentSettingsPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/settings",
  });

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-teal-700">
          Profile &amp; Preferences
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">
          Update learning preferences
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Adjust your target language, study schedule, or explanation language at
          any time.
        </p>
      </div>

      <OnboardingForm
        mode="settings"
        accessToken={accessToken}
        initialUser={user}
      />
    </div>
  );
}
