import { notFound, redirect } from "next/navigation";
import { LessonViewer } from "@/features/learning/lesson-viewer";
import { ApiClientError, fetchLessonDetail } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

interface LessonDetailPageProps {
  params: Promise<{ slug: string }>;
}

export default async function StudentLessonDetailPage({
  params,
}: LessonDetailPageProps) {
  const { slug } = await params;
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: `/student/lessons/${slug}`,
  });

  if (!user.onboarding_completed) {
    redirect("/student/onboarding");
  }

  let lesson;
  try {
    lesson = await fetchLessonDetail(accessToken, slug);
  } catch (err) {
    if (err instanceof ApiClientError && err.status === 404) {
      notFound();
    }
    throw err;
  }

  return (
    <LessonViewer
      accessToken={accessToken}
      initialLesson={lesson}
      initialLanguage={user.preferences?.preferred_explanation_language ?? "en"}
    />
  );
}
