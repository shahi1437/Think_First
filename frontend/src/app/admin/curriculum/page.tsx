import { fetchAdminLessons, fetchAdminTracks } from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";
import { CurriculumManagerClient } from "@/features/admin/curriculum-manager-client";

export const dynamic = "force-dynamic";

export default async function AdminCurriculumPage() {
  const { accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["admin"],
    currentPath: "/admin/curriculum",
  });

  const [tracks, lessons] = await Promise.all([
    fetchAdminTracks(accessToken),
    fetchAdminLessons(accessToken),
  ]);

  return (
    <CurriculumManagerClient
      accessToken={accessToken}
      initialTracks={tracks}
      initialLessons={lessons}
    />
  );
}
