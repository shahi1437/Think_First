import { OnboardingForm } from "@/features/onboarding/onboarding-form";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export default async function StudentSettingsPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/settings",
  });

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-teal-700">
          Profile &amp; Preferences
        </p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">
          Update Learning Preferences
        </h1>
        <p className="mt-2 text-base text-slate-600">
          Adjust your target language, daily practice time, or explanation
          language whenever you need.
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
