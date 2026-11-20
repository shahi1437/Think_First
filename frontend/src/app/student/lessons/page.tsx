import { ArrowRight, BookOpen, CheckCircle2, Clock } from "lucide-react";
import Link from "next/link";
import { redirect } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { fetchLessons } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export default async function StudentLessonsPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/lessons",
  });

  if (!user.onboarding_completed) {
    redirect("/student/onboarding");
  }

  const lessons = await fetchLessons(accessToken);
  const completedCount = lessons.filter(
    (lsn) => lsn.progress_status === "completed",
  ).length;

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
              Guided Python Curriculum
            </p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900">
              Beginner Python Lessons
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Learn step-by-step in English or Bangla with interactive examples
              and real Judge0 guided practice exercises.
            </p>
          </div>
          <Badge variant="indigo">
            <BookOpen className="h-3.5 w-3.5" aria-hidden="true" />
            <span>
              {completedCount} / {lessons.length} completed
            </span>
          </Badge>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {lessons.map((lesson) => (
          <article
            key={lesson.lesson_id}
            className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-indigo-300"
          >
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-semibold text-slate-500">
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
                      <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                    ) : null}
                    <span className="capitalize">
                      {lesson.progress_status.replaceAll("_", " ")}
                    </span>
                  </Badge>
                  <Badge variant="teal">{lesson.skill_slug}</Badge>
                </div>
              </div>

              <h2 className="mt-2 text-base font-bold text-slate-900">
                {lesson.title_en}
              </h2>
              <p className="mt-0.5 text-xs font-medium text-indigo-800">
                {lesson.title_bn}
              </p>
              <p className="mt-2 text-xs leading-relaxed text-slate-600">
                {lesson.summary_en}
              </p>

              <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-3 w-3" aria-hidden="true" />
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

            <div className="mt-4 pt-2">
              <Link
                href={`/student/lessons/${lesson.slug}`}
                className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-indigo-500"
              >
                <span>
                  {lesson.progress_status === "completed"
                    ? "Review Lesson"
                    : "Open Lesson & Practice"}
                </span>
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
