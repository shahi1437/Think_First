import {
  fetchAdminDiagnostics,
  fetchAdminKnowledgeDocs,
} from "@/lib/api-client";
import { requireAuthenticatedUser } from "@/lib/auth/server-guard";
import { DiagnosticsKnowledgeClient } from "@/features/admin/diagnostics-knowledge-client";

export const dynamic = "force-dynamic";

export default async function AdminDiagnosticsPage() {
  const { accessToken } = await requireAuthenticatedUser({
    allowedRoles: ["admin"],
    currentPath: "/admin/diagnostics",
  });

  const [questions, docs] = await Promise.all([
    fetchAdminDiagnostics(accessToken),
    fetchAdminKnowledgeDocs(accessToken),
  ]);

  return (
    <DiagnosticsKnowledgeClient
      accessToken={accessToken}
      initialQuestions={questions}
      initialKnowledgeDocs={docs}
    />
  );
}
