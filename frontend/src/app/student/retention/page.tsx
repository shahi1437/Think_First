import { RetentionClient } from "@/features/growth/retention-client";
import { fetchRetentionOverview } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";

export const dynamic = "force-dynamic";

export default async function StudentRetentionPage() {
  const { user, accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["student", "teacher", "admin"],
    currentPath: "/student/retention",
  });

  const overview = await fetchRetentionOverview(accessToken);

  return (
    <RetentionClient
      accessToken={accessToken}
      initialOverview={overview}
      initialLanguage={
        user.preferences?.preferred_explanation_language ?? "en"
      }
    />
  );
}
