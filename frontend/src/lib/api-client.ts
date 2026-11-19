import { z } from "zod";
import { publicEnv } from "@/lib/env";
import {
  userMeResponseSchema,
  type OnboardingFormValues,
  type UserMeResponse,
} from "@/types/identity";
import {
  adminProblemDetailSchema,
  adminValidationReportSchema,
  languageItemSchema,
  paginatedAdminProblemsSchema,
  paginatedProblemsSchema,
  paginatedSubmissionsSchema,
  revisionResponseSchema,
  studentProblemDetailSchema,
  submissionResponseSchema,
  type AdminProblemDetail,
  type AdminProblemListItem,
  type AdminValidationReport,
  type Difficulty,
  type ProblemMode,
  type ProblemStatus,
  type RevisionResponse,
  type StudentProblemDetail,
  type StudentProblemListItem,
  type SubmissionResponse,
  type SubmissionSummaryItem,
} from "@/types/problems";

export const apiMetaSchema = z.object({
  service: z.string(),
  api_version: z.literal("v1"),
  app_version: z.string(),
  environment: z.string(),
  request_id: z.string(),
});

export const healthReadySchema = z.object({
  status: z.enum(["ok", "degraded"]),
  service: z.string(),
  version: z.string(),
  database: z.enum(["ok", "unavailable"]),
});

export type ApiMeta = z.infer<typeof apiMetaSchema>;
export type HealthReady = z.infer<typeof healthReadySchema>;

export interface BackendConnectivityStatus {
  meta: ApiMeta;
  readiness: HealthReady;
  readinessHttpStatus: number;
}

export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(message: string, status: number, code = "API_ERROR") {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
  }
}

async function parseErrorResponse(response: Response): Promise<ApiClientError> {
  try {
    const data = (await response.json()) as {
      code?: string;
      message?: string;
    };
    return new ApiClientError(
      data.message || `Request failed with HTTP ${response.status}`,
      response.status,
      data.code || `HTTP_${response.status}`,
    );
  } catch {
    return new ApiClientError(
      `Request failed with HTTP ${response.status}`,
      response.status,
      `HTTP_${response.status}`,
    );
  }
}

function authHeaders(accessToken: string, json = false): HeadersInit {
  return {
    Accept: "application/json",
    Authorization: `Bearer ${accessToken}`,
    ...(json ? { "Content-Type": "application/json" } : {}),
  };
}

export async function fetchBackendConnectivity(
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<BackendConnectivityStatus> {
  const [metaResponse, readyResponse] = await Promise.all([
    fetch(`${baseUrl}/api/v1/meta`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    }),
    fetch(`${baseUrl}/health/ready`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    }),
  ]);

  if (!metaResponse.ok) {
    throw new ApiClientError(
      `API metadata check failed with HTTP ${metaResponse.status}`,
      metaResponse.status,
      "META_CHECK_FAILED",
    );
  }

  const metaJson: unknown = await metaResponse.json();
  const readyJson: unknown = await readyResponse.json();

  return {
    meta: apiMetaSchema.parse(metaJson),
    readiness: healthReadySchema.parse(readyJson),
    readinessHttpStatus: readyResponse.status,
  };
}

export async function fetchCurrentUser(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<UserMeResponse> {
  const response = await fetch(`${baseUrl}/api/v1/users/me`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return userMeResponseSchema.parse(await response.json());
}

export async function submitOnboarding(
  accessToken: string,
  values: OnboardingFormValues,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<UserMeResponse> {
  const response = await fetch(`${baseUrl}/api/v1/users/me/onboarding`, {
    method: "POST",
    headers: authHeaders(accessToken, true),
    body: JSON.stringify(values),
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return userMeResponseSchema.parse(await response.json());
}

export async function updateUserPreferences(
  accessToken: string,
  values: Partial<Omit<OnboardingFormValues, "full_name">>,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<UserMeResponse> {
  const response = await fetch(`${baseUrl}/api/v1/users/me/preferences`, {
    method: "PATCH",
    headers: authHeaders(accessToken, true),
    body: JSON.stringify(values),
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return userMeResponseSchema.parse(await response.json());
}

// --- Phase 3: Problem Bank, Execution & Revisions ---

export async function fetchProblems(
  accessToken: string,
  params?: {
    search?: string;
    difficulty?: Difficulty | "";
    mode?: ProblemMode | "";
    topic?: string;
    limit?: number;
    offset?: number;
  },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<{ items: StudentProblemListItem[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.search) query.set("search", params.search);
  if (params?.difficulty) query.set("difficulty", params.difficulty);
  if (params?.mode) query.set("mode", params.mode);
  if (params?.topic) query.set("topic", params.topic);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));
  const qs = query.toString();

  const response = await fetch(
    `${baseUrl}/api/v1/problems${qs ? `?${qs}` : ""}`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return paginatedProblemsSchema.parse(await response.json());
}

export async function fetchProblemDetail(
  accessToken: string,
  problemId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<StudentProblemDetail> {
  const response = await fetch(`${baseUrl}/api/v1/problems/${problemId}`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return studentProblemDetailSchema.parse(await response.json());
}

export async function createSubmission(
  accessToken: string,
  payload: {
    problem_id: string;
    language_slug: string;
    submission_kind: "run" | "submit";
    source_code: string;
    prediction_text?: string;
    explanation_text?: string;
  },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<SubmissionResponse> {
  const response = await fetch(`${baseUrl}/api/v1/submissions`, {
    method: "POST",
    headers: authHeaders(accessToken, true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return submissionResponseSchema.parse(await response.json());
}

export async function fetchMySubmissions(
  accessToken: string,
  problemId?: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<{ items: SubmissionSummaryItem[]; total: number }> {
  const qs = problemId ? `?problem_id=${encodeURIComponent(problemId)}` : "";
  const response = await fetch(`${baseUrl}/api/v1/submissions${qs}`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return paginatedSubmissionsSchema.parse(await response.json());
}

export async function fetchSubmissionDetail(
  accessToken: string,
  submissionId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<SubmissionResponse> {
  const response = await fetch(
    `${baseUrl}/api/v1/submissions/${submissionId}`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return submissionResponseSchema.parse(await response.json());
}

export async function saveWorkspaceRevision(
  accessToken: string,
  payload: {
    problem_version_id: string;
    language_slug: string;
    source_code: string;
    prediction_text?: string;
    explanation_text?: string;
    revision_type: "autosave" | "manual";
  },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<RevisionResponse> {
  const response = await fetch(`${baseUrl}/api/v1/workspace/revisions`, {
    method: "PUT",
    headers: authHeaders(accessToken, true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return revisionResponseSchema.parse(await response.json());
}

export async function fetchWorkspaceRevisions(
  accessToken: string,
  problemVersionId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<RevisionResponse[]> {
  const response = await fetch(
    `${baseUrl}/api/v1/workspace/revisions?problem_version_id=${encodeURIComponent(problemVersionId)}`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return z.array(revisionResponseSchema).parse(await response.json());
}

// --- Phase 3: Admin Problem Studio ---

export async function fetchAdminProblems(
  accessToken: string,
  params?: { status?: ProblemStatus | ""; search?: string },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<{ items: AdminProblemListItem[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.search) query.set("search", params.search);
  const qs = query.toString();
  const response = await fetch(
    `${baseUrl}/api/v1/admin/problems${qs ? `?${qs}` : ""}`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return paginatedAdminProblemsSchema.parse(await response.json());
}

export async function fetchAdminProblemDetail(
  accessToken: string,
  problemId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminProblemDetail> {
  const response = await fetch(`${baseUrl}/api/v1/admin/problems/${problemId}`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return adminProblemDetailSchema.parse(await response.json());
}

export async function createAdminProblem(
  accessToken: string,
  payload: Record<string, unknown>,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminProblemDetail> {
  const response = await fetch(`${baseUrl}/api/v1/admin/problems`, {
    method: "POST",
    headers: authHeaders(accessToken, true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return adminProblemDetailSchema.parse(await response.json());
}

export async function updateAdminProblem(
  accessToken: string,
  problemId: string,
  payload: Record<string, unknown>,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminProblemDetail> {
  const response = await fetch(`${baseUrl}/api/v1/admin/problems/${problemId}`, {
    method: "PATCH",
    headers: authHeaders(accessToken, true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return adminProblemDetailSchema.parse(await response.json());
}

export async function validateAdminProblem(
  accessToken: string,
  problemId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminValidationReport> {
  const response = await fetch(
    `${baseUrl}/api/v1/admin/problems/${problemId}/validate`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return adminValidationReportSchema.parse(await response.json());
}

export async function approveAdminProblem(
  accessToken: string,
  problemId: string,
  notes: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminProblemDetail> {
  const response = await fetch(
    `${baseUrl}/api/v1/admin/problems/${problemId}/approve`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ notes }),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return adminProblemDetailSchema.parse(await response.json());
}

export async function publishAdminProblem(
  accessToken: string,
  problemId: string,
  notes: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminProblemDetail> {
  const response = await fetch(
    `${baseUrl}/api/v1/admin/problems/${problemId}/publish`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ notes }),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return adminProblemDetailSchema.parse(await response.json());
}

export async function syncAdminLanguages(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<{ synced_count: number; languages: z.infer<typeof languageItemSchema>[] }> {
  const response = await fetch(`${baseUrl}/api/v1/admin/languages/sync`, {
    method: "POST",
    headers: authHeaders(accessToken),
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return z
    .object({
      synced_count: z.number().int(),
      languages: z.array(languageItemSchema),
    })
    .parse(await response.json());
}
