import { LearningDnaClient } from "@/features/growth/learning-dna-client";
import { fetchLearningDnaProfile } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function StudentLearningDnaPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/dna",
  });

  const profile = await fetchLearningDnaProfile(accessToken);

  return (
    <LearningDnaClient
      accessToken={accessToken}
      initialProfile={profile}
      initialLanguage={
        user.preferences?.preferred_explanation_language ?? "en"
      }
    />
  );
}
