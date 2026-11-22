import { ArrowRight, BookOpen, CheckCircle2, Clock } from "lucide-react";
import Link from "next/link";
import { redirect } from "next/navigation";
import { LanguageSelector } from "@/components/language-selector";
import { Badge } from "@/components/ui/badge";
import {
  fetchLanguageProgressOverview,
  fetchLessons,
} from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";
import { getLanguageDisplayName } from "@/lib/languages";

export const dynamic = "force-dynamic";

export default async function StudentLessonsPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/lessons",
  });

  if (!user.onboarding_completed) {
    redirect("/student/onboarding");
  }

  const [languageOverview, lessons] = await Promise.all([
    fetchLanguageProgressOverview(accessToken),
    fetchLessons(accessToken),
  ]);
  const completedCount = lessons.filter(
    (lsn) => lsn.progress_status === "completed",
  ).length;
  const activeLanguageLabel = getLanguageDisplayName(
    languageOverview.active_language_slug,
  );
  const explanationLang =
    user.preferences?.preferred_explanation_language ?? "en";

  return (
    <div className="space-y-6">
      <LanguageSelector
        key={languageOverview.active_language_slug}
        accessToken={accessToken}
        initialOverview={languageOverview}
        explanationLanguage={explanationLang}
        compact
      />

      <div className="tf-animate-enter rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-7">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
              Guided {activeLanguageLabel} Curriculum
            </p>
            <h1 className="mt-1.5 text-3xl font-bold tracking-tight text-slate-900 sm:text-[34px]">
              {activeLanguageLabel} Guided Lessons
            </h1>
            <p className="mt-2 max-w-2xl text-base leading-relaxed text-slate-600">
              Learn {activeLanguageLabel} step-by-step in English or Bangla with
              interactive examples and real sandbox-executed guided exercises.
            </p>
          </div>
          <Badge variant="indigo">
            <BookOpen className="h-4 w-4" aria-hidden="true" />
            <span className="text-sm">
              {completedCount} / {lessons.length} completed
            </span>
          </Badge>
        </div>
        {lessons.length > 0 ? (
          <div className="mt-4">
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className="tf-progress-fill h-full rounded-full bg-gradient-to-r from-indigo-500 to-teal-500"
                style={{
                  width: `${Math.round((completedCount / lessons.length) * 100)}%`,
                }}
              />
            </div>
          </div>
        ) : null}
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        {lessons.map((lesson) => (
          <article
            key={lesson.lesson_id}
            className="tf-card-interactive flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-6 shadow-sm hover:border-indigo-300"
          >
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Lesson {lesson.display_order}
                </span>
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge
                    variant={
                      lesson.progress_status === "completed"
                        ? "emerald"
                        : lesson.progress_status === "in_progress"
                          ? "indigo"
                          : "neutral"
                    }
                  >
                    {lesson.progress_status === "completed" ? (
                      <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                    ) : null}
                    <span className="capitalize">
                      {lesson.progress_status.replaceAll("_", " ")}
                    </span>
                  </Badge>
                  <Badge variant="teal">{lesson.skill_slug}</Badge>
                </div>
              </div>

              <h2 className="mt-3 text-xl font-bold text-slate-900">
                {lesson.title_en}
              </h2>
              <p className="mt-1 text-sm font-medium text-indigo-800">
                {lesson.title_bn}
              </p>
              <p className="mt-2.5 text-[15px] leading-relaxed text-slate-600">
                {lesson.summary_en}
              </p>

              <div className="mt-3.5 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                  {lesson.estimated_minutes} min
                </span>
                <span>·</span>
                <span>
                  {lesson.prerequisites_met
                    ? "Prerequisites satisfied"
                    : `Recommended prereq: ${lesson.prerequisite_lesson_slugs.join(", ")}`}
                </span>
              </div>
            </div>

            <div className="mt-5 pt-2">
              <Link
                href={`/student/lessons/${lesson.slug}`}
                className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-[15px] font-semibold text-white transition hover:bg-indigo-500"
              >
                <span>
                  {lesson.progress_status === "completed"
                    ? "Review Lesson"
                    : "Open Lesson & Practice"}
                </span>
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
