import Link from "next/link";
import { redirect } from "next/navigation";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export default async function StudentDashboardPage() {
  const { user } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student",
  });

  if (!user.onboarding_completed) {
    redirect("/student/onboarding");
  }

  const prefs = user.preferences;

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wider text-teal-700">
          Student Workspace
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">
          Welcome back, {user.full_name || user.email}
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Your learning preferences are persisted securely. Topic competency will
          appear as you complete verified coding, debugging, and diagnostic tasks.
        </p>
      </div>

      {prefs ? (
        <section
          aria-labelledby="recommended-entry-heading"
          className="grid gap-6 md:grid-cols-2"
        >
          <div className="rounded-2xl border border-indigo-200 bg-white p-6 shadow-sm">
            <h2
              id="recommended-entry-heading"
              className="text-base font-semibold text-slate-900"
            >
              Recommended Starting Track
            </h2>
            <p className="mt-2 inline-flex rounded-md bg-indigo-50 px-2.5 py-1 font-mono text-xs font-semibold text-indigo-800">
              {prefs.recommended_entry_track}
            </p>
            <p className="mt-3 text-sm leading-relaxed text-slate-600">
              {prefs.recommendation_rationale}
            </p>
            <div className="mt-4">
              <Link
                href="/student/problems"
                className="inline-flex items-center rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-indigo-700"
              >
                Open Problem Bank &amp; Coding Workspace
              </Link>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-900">
                Active Study Preferences
              </h2>
              <Link
                href="/student/settings"
                className="text-xs font-medium text-indigo-700 hover:underline"
              >
                Edit preferences
              </Link>
            </div>
            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-500">Language</dt>
                <dd className="font-medium uppercase text-slate-900">
                  {prefs.preferred_language}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Daily target</dt>
                <dd className="font-medium text-slate-900">
                  {prefs.daily_practice_minutes} minutes/day
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Explanation language</dt>
                <dd className="font-medium uppercase text-slate-900">
                  {prefs.preferred_explanation_language}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-500">Learning goal</dt>
                <dd className="font-medium text-slate-900">
                  {prefs.learning_goal.replaceAll("_", " ")}
                </dd>
              </div>
            </dl>
          </div>
        </section>
      ) : null}
    </div>
  );
}
