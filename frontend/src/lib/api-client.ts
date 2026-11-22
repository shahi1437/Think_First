import { z } from "zod";
import { publicEnv } from "@/lib/env";
import {
  userMeResponseSchema,
  type OnboardingFormValues,
  type UserMeResponse,
} from "@/types/identity";
import {
  adminProblemArchiveResponseSchema,
  adminProblemDetailSchema,
  adminProblemVersionsResponseSchema,
  adminValidationReportSchema,
  languageItemSchema,
  paginatedAdminProblemsSchema,
  paginatedProblemsSchema,
  paginatedSubmissionsSchema,
  revisionResponseSchema,
  studentProblemDetailSchema,
  submissionResponseSchema,
  type AdminProblemArchiveResponse,
  type AdminProblemDetail,
  type AdminProblemListItem,
  type AdminProblemVersionsResponse,
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
import {
  adminAuditLogItemSchema,
  adminCurriculumValidateResponseSchema,
  adminDashboardOverviewSchema,
  adminDiagnosticQuestionDetailSchema,
  adminLessonDetailViewSchema,
  adminOperationsHealthSchema,
  adminUserSummarySchema,
  knowledgeDocumentSchema,
  type AdminAuditLogItem,
  type AdminCurriculumValidateResponse,
  type AdminDashboardOverview,
  type AdminDiagnosticQuestionDetail,
  type AdminLessonDetailView,
  type AdminOperationsHealth,
  type AdminUserSummary,
  type KnowledgeDocumentItem,
} from "@/types/admin";
import {
  learningEventViewSchema,
  mentorSessionDetailSchema,
  mlDiagnosisResponseSchema,
  transferChallengeSummarySchema,
  verificationAttemptViewSchema,
  type LearningEventView,
  type MentorSessionDetail,
  type MLDiagnosisResponse,
  type TransferChallengeSummary,
  type VerificationAttemptView,
} from "@/types/mentor";
import {
  diagnosticSessionViewSchema,
  languageProgressOverviewSchema,
  learningDashboardViewSchema,
  learningTrackViewSchema,
  lessonDetailViewSchema,
  lessonExerciseRunResponseSchema,
  lessonSummaryViewSchema,
  skillGraphViewSchema,
  studentTrackStatusSchema,
  type DiagnosticSessionView,
  type LanguageProgressOverview,
  type LanguageSlug,
  type LearningDashboardView,
  type LearningTrackView,
  type LessonDetailView,
  type LessonExerciseRunResponse,
  type LessonSummaryView,
  type SkillGraphView,
  type StudentTrackStatus,
  type TrackSlug,
} from "@/types/learning";
import {
  dailyLearningPlanViewSchema,
  dailyPlanWorkspaceViewSchema,
  learningDnaProfileViewSchema,
  learningHistoryResponseViewSchema,
  retentionAttemptViewSchema,
  retentionOverviewViewSchema,
  type DailyLearningPlanView,
  type DailyPlanWorkspaceView,
  type DailyTaskStatus,
  type HistoryCategory,
  type LearningDnaProfileView,
  type LearningHistoryResponseView,
  type RetentionAttemptView,
  type RetentionOverviewView,
} from "@/types/growth";
import {
  assignmentSummaryViewSchema,
  classInvitationViewSchema,
  courseSummaryViewSchema,
  rosterMemberViewSchema,
  studentAssignmentAttemptResponseSchema,
  studentAssignmentDetailViewSchema,
  studentAssignmentListItemViewSchema,
  studentEnrolledCourseViewSchema,
  teacherAssignmentDetailViewSchema,
  teacherCourseDetailViewSchema,
  teacherDashboardViewSchema,
  teacherSubmissionReviewItemSchema,
  type AssignmentSummaryView,
  type ClassInvitationView,
  type CourseSummaryView,
  type EnrollmentPolicy,
  type GradingPolicy,
  type RosterMemberView,
  type StudentAssignmentAttemptResponse,
  type StudentAssignmentDetailView,
  type StudentAssignmentFilter,
  type StudentAssignmentListItemView,
  type StudentEnrolledCourseView,
  type TeacherAssignmentDetailView,
  type TeacherCourseDetailView,
  type TeacherDashboardView,
  type TeacherSubmissionReviewItem,
} from "@/types/classroom";

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

export class BackendUnavailableError extends Error {
  readonly code = "BACKEND_UNAVAILABLE";

  constructor(
    message = "Unable to connect to the Think_First learning service right now. Please try again in a moment.",
  ) {
    super(message);
    this.name = "BackendUnavailableError";
  }
}

const DEFAULT_TIMEOUT_MS = 15_000;
const HEALTH_TIMEOUT_MS = 8_000;
const EXECUTION_TIMEOUT_MS = 60_000;

async function safeFetch(
  input: string,
  init?: RequestInit,
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController();
  let timedOut = false;

  const externalSignal = init?.signal;
  const onExternalAbort = () => controller.abort(externalSignal?.reason);
  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort(externalSignal.reason);
    } else {
      externalSignal.addEventListener("abort", onExternalAbort, { once: true });
    }
  }

  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (err) {
    if (timedOut) {
      throw new BackendUnavailableError(
        "The Think_First learning server took too long to respond. Please try again in a moment.",
      );
    }
    if (externalSignal?.aborted) {
      throw err;
    }
    throw new BackendUnavailableError();
  } finally {
    clearTimeout(timer);
    if (externalSignal) {
      externalSignal.removeEventListener("abort", onExternalAbort);
    }
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
    safeFetch(
      `${baseUrl}/api/v1/meta`,
      {
        headers: { Accept: "application/json" },
        cache: "no-store",
      },
      HEALTH_TIMEOUT_MS,
    ),
    safeFetch(
      `${baseUrl}/health/ready`,
      {
        headers: { Accept: "application/json" },
        cache: "no-store",
      },
      HEALTH_TIMEOUT_MS,
    ),
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
  const response = await safeFetch(`${baseUrl}/api/v1/users/me`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return userMeResponseSchema.parse(await response.json());
}

export async function verifyLoginPortal(
  accessToken: string,
  portal: "student" | "teacher" | "admin",
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<UserMeResponse> {
  const response = await safeFetch(`${baseUrl}/api/v1/users/me/verify-portal`, {
    method: "POST",
    headers: authHeaders(accessToken, true),
    body: JSON.stringify({ portal }),
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
  const response = await safeFetch(`${baseUrl}/api/v1/users/me/onboarding`, {
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
  const response = await safeFetch(`${baseUrl}/api/v1/users/me/preferences`, {
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
    language?: string;
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
  if (params?.language) query.set("language", params.language);
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));
  const qs = query.toString();

  const response = await safeFetch(
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
  const response = await safeFetch(`${baseUrl}/api/v1/problems/${problemId}`, {
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
  const response = await safeFetch(
    `${baseUrl}/api/v1/submissions`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify(payload),
    },
    EXECUTION_TIMEOUT_MS,
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return submissionResponseSchema.parse(await response.json());
}

export async function fetchMySubmissions(
  accessToken: string,
  problemId?: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<{ items: SubmissionSummaryItem[]; total: number }> {
  const qs = problemId ? `?problem_id=${encodeURIComponent(problemId)}` : "";
  const response = await safeFetch(`${baseUrl}/api/v1/submissions${qs}`, {
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
  const response = await safeFetch(
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
  const response = await safeFetch(`${baseUrl}/api/v1/workspace/revisions`, {
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
  const response = await safeFetch(
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
  params?: { status?: ProblemStatus | ""; search?: string; limit?: number },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<{ items: AdminProblemListItem[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.search) query.set("search", params.search);
  if (params?.limit) query.set("limit", String(params.limit));
  const qs = query.toString();
  const response = await safeFetch(
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
  const response = await safeFetch(`${baseUrl}/api/v1/admin/problems/${problemId}`, {
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
  const response = await safeFetch(`${baseUrl}/api/v1/admin/problems`, {
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
  const response = await safeFetch(`${baseUrl}/api/v1/admin/problems/${problemId}`, {
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
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/problems/${problemId}/validate`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
    },
    EXECUTION_TIMEOUT_MS,
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
  const response = await safeFetch(
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
  const response = await safeFetch(
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
  const response = await safeFetch(`${baseUrl}/api/v1/admin/languages/sync`, {
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

// --- Phase 4: AI Mentor, ML Diagnosis, RAG & Independent Transfer Verification ---

export async function startOrResumeMentorSession(
  accessToken: string,
  payload: {
    problem_id: string;
    submission_id?: string | null;
    explanation_language?: "en" | "bn";
  },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<MentorSessionDetail> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/mentor/sessions`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify(payload),
    },
    EXECUTION_TIMEOUT_MS,
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return mentorSessionDetailSchema.parse(await response.json());
}

export async function sendMentorTurn(
  accessToken: string,
  sessionId: string,
  payload: {
    action: "diagnose" | "respond" | "request_hint";
    submission_id?: string | null;
    student_message?: string;
    requested_hint_level?: 1 | 2 | 3;
    explanation_language?: "en" | "bn";
  },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<MentorSessionDetail> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/mentor/sessions/${sessionId}/turns`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify(payload),
    },
    EXECUTION_TIMEOUT_MS,
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return mentorSessionDetailSchema.parse(await response.json());
}

export async function diagnoseSubmission(
  accessToken: string,
  submissionId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<MLDiagnosisResponse> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/mentor/diagnose/${submissionId}`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return mlDiagnosisResponseSchema.parse(await response.json());
}

export async function fetchTransferChallenge(
  accessToken: string,
  sourceProblemId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<TransferChallengeSummary | null> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/verifications/problem/${sourceProblemId}`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  const raw: unknown = await response.json();
  if (raw === null) return null;
  return transferChallengeSummarySchema.parse(raw);
}

export async function submitTransferVerificationAttempt(
  accessToken: string,
  verificationLinkId: string,
  payload: {
    source_submission_id?: string | null;
    language_slug: string;
    source_code: string;
    student_explanation: string;
  },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<VerificationAttemptView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/verifications/${verificationLinkId}/attempts`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify(payload),
    },
    EXECUTION_TIMEOUT_MS,
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return verificationAttemptViewSchema.parse(await response.json());
}

export async function fetchMyLearningEvents(
  accessToken: string,
  limit = 20,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<LearningEventView[]> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/learning/events?limit=${limit}`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return z.array(learningEventViewSchema).parse(await response.json());
}

// --- Phase 5 + Multi-Language: Languages, Tracks, Bilingual Lessons, Diagnostics & Skill Graph ---

export async function fetchLanguageProgressOverview(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<LanguageProgressOverview> {
  const response = await safeFetch(`${baseUrl}/api/v1/learning/languages`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return languageProgressOverviewSchema.parse(await response.json());
}

export async function selectActiveLanguage(
  accessToken: string,
  languageSlug: LanguageSlug,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<LanguageProgressOverview> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/learning/languages/select`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ language_slug: languageSlug }),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return languageProgressOverviewSchema.parse(await response.json());
}

export async function fetchLearningDashboard(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<LearningDashboardView> {
  const response = await safeFetch(`${baseUrl}/api/v1/learning/dashboard`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return learningDashboardViewSchema.parse(await response.json());
}

export async function selectLearningTrack(
  accessToken: string,
  trackSlug: TrackSlug,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<StudentTrackStatus> {
  const response = await safeFetch(`${baseUrl}/api/v1/learning/tracks/select`, {
    method: "POST",
    headers: authHeaders(accessToken, true),
    body: JSON.stringify({ track_slug: trackSlug }),
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return studentTrackStatusSchema.parse(await response.json());
}

export async function fetchLessons(
  accessToken: string,
  trackSlug?: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<LessonSummaryView[]> {
  const qs = trackSlug ? `?track=${encodeURIComponent(trackSlug)}` : "";
  const response = await safeFetch(`${baseUrl}/api/v1/learning/lessons${qs}`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return z.array(lessonSummaryViewSchema).parse(await response.json());
}

export async function fetchLessonDetail(
  accessToken: string,
  slug: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<LessonDetailView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/learning/lessons/${encodeURIComponent(slug)}`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return lessonDetailViewSchema.parse(await response.json());
}

export async function markLessonReadingComplete(
  accessToken: string,
  lessonId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<LessonDetailView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/learning/lessons/${lessonId}/reading`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ reading_completed: true }),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return lessonDetailViewSchema.parse(await response.json());
}

export async function runLessonGuidedExercise(
  accessToken: string,
  lessonId: string,
  sourceCode: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<LessonExerciseRunResponse> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/learning/lessons/${lessonId}/exercise/run`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ source_code: sourceCode }),
    },
    EXECUTION_TIMEOUT_MS,
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return lessonExerciseRunResponseSchema.parse(await response.json());
}

export async function startOrResumeDiagnosticSession(
  accessToken: string,
  explanationLanguage: "en" | "bn" = "en",
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<DiagnosticSessionView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/learning/diagnostics/sessions`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ explanation_language: explanationLanguage }),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return diagnosticSessionViewSchema.parse(await response.json());
}

export async function fetchMyDiagnosticSessions(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<DiagnosticSessionView[]> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/learning/diagnostics/sessions`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return z.array(diagnosticSessionViewSchema).parse(await response.json());
}

export async function submitDiagnosticAnswer(
  accessToken: string,
  sessionId: string,
  payload: {
    question_id: string;
    selected_option_id?: string;
    source_code?: string;
    response_time_ms?: number;
  },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<DiagnosticSessionView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/learning/diagnostics/sessions/${sessionId}/answers`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify(payload),
    },
    EXECUTION_TIMEOUT_MS,
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return diagnosticSessionViewSchema.parse(await response.json());
}

export async function fetchStudentSkillGraph(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<SkillGraphView> {
  const response = await safeFetch(`${baseUrl}/api/v1/learning/skill-graph`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return skillGraphViewSchema.parse(await response.json());
}

// =============================================================================
// Phase 6: Learning DNA, Adaptive Daily Plan, Persistent History & Retention
// =============================================================================

export async function fetchLearningDnaProfile(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<LearningDnaProfileView> {
  const response = await safeFetch(`${baseUrl}/api/v1/growth/learning-dna`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return learningDnaProfileViewSchema.parse(await response.json());
}

export async function fetchDailyPlanWorkspace(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<DailyPlanWorkspaceView> {
  const response = await safeFetch(`${baseUrl}/api/v1/growth/daily-plan`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return dailyPlanWorkspaceViewSchema.parse(await response.json());
}

export async function regenerateDailyPlan(
  accessToken: string,
  availableMinutes?: number,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<DailyPlanWorkspaceView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/growth/daily-plan/regenerate`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify(
        availableMinutes ? { available_minutes: availableMinutes } : {},
      ),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return dailyPlanWorkspaceViewSchema.parse(await response.json());
}

export async function updateDailyPlanTaskStatus(
  accessToken: string,
  taskId: string,
  status: DailyTaskStatus,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<DailyLearningPlanView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/growth/daily-plan/tasks/${taskId}`,
    {
      method: "PATCH",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ status }),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return dailyLearningPlanViewSchema.parse(await response.json());
}

export async function fetchLearningHistory(
  accessToken: string,
  params: {
    q?: string;
    category?: HistoryCategory | "";
    limit?: number;
    offset?: number;
  } = {},
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<LearningHistoryResponseView> {
  const sp = new URLSearchParams();
  if (params.q?.trim()) sp.set("q", params.q.trim());
  if (params.category) sp.set("category", params.category);
  if (params.limit) sp.set("limit", String(params.limit));
  if (params.offset) sp.set("offset", String(params.offset));
  const qs = sp.toString();
  const response = await safeFetch(
    `${baseUrl}/api/v1/growth/history${qs ? `?${qs}` : ""}`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return learningHistoryResponseViewSchema.parse(await response.json());
}

export async function fetchRetentionOverview(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<RetentionOverviewView> {
  const response = await safeFetch(`${baseUrl}/api/v1/growth/retention`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return retentionOverviewViewSchema.parse(await response.json());
}

export async function submitRetentionAttempt(
  accessToken: string,
  scheduleId: string,
  payload: {
    language_slug?: string;
    source_code: string;
    student_explanation: string;
  },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<RetentionAttemptView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/growth/retention/${scheduleId}/attempts`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({
        language_slug: payload.language_slug ?? "python",
        source_code: payload.source_code,
        student_explanation: payload.student_explanation,
      }),
    },
    EXECUTION_TIMEOUT_MS,
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return retentionAttemptViewSchema.parse(await response.json());
}

// =============================================================================
// Phase 7: Teacher Dashboard, Classrooms, Assignments, Grading & Student Portal
// =============================================================================

export async function fetchTeacherDashboard(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<TeacherDashboardView> {
  const response = await safeFetch(`${baseUrl}/api/v1/teacher/dashboard`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return teacherDashboardViewSchema.parse(await response.json());
}

export async function fetchTeacherClasses(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<CourseSummaryView[]> {
  const response = await safeFetch(`${baseUrl}/api/v1/teacher/classes`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return z.array(courseSummaryViewSchema).parse(await response.json());
}

export async function createTeacherClass(
  accessToken: string,
  payload: {
    code: string;
    title: string;
    description?: string;
    term?: string;
    enrollment_policy?: EnrollmentPolicy;
    allow_student_leave?: boolean;
  },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<CourseSummaryView> {
  const response = await safeFetch(`${baseUrl}/api/v1/teacher/classes`, {
    method: "POST",
    headers: authHeaders(accessToken, true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return courseSummaryViewSchema.parse(await response.json());
}

export async function fetchTeacherClassDetail(
  accessToken: string,
  courseId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<TeacherCourseDetailView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/teacher/classes/${courseId}`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return teacherCourseDetailViewSchema.parse(await response.json());
}

export async function updateTeacherClass(
  accessToken: string,
  courseId: string,
  payload: {
    code?: string;
    title?: string;
    description?: string;
    term?: string;
    enrollment_policy?: EnrollmentPolicy;
    allow_student_leave?: boolean;
  },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<CourseSummaryView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/teacher/classes/${courseId}`,
    {
      method: "PATCH",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return courseSummaryViewSchema.parse(await response.json());
}

export async function archiveTeacherClass(
  accessToken: string,
  courseId: string,
  archive = true,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<CourseSummaryView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/teacher/classes/${courseId}/archive?archive=${archive}`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return courseSummaryViewSchema.parse(await response.json());
}

export async function createClassInvitation(
  accessToken: string,
  courseId: string,
  payload: { max_uses?: number | null; expires_in_hours?: number | null } = {},
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<ClassInvitationView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/teacher/classes/${courseId}/invitations`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return classInvitationViewSchema.parse(await response.json());
}

export async function revokeClassInvitation(
  accessToken: string,
  courseId: string,
  invitationId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<ClassInvitationView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/teacher/classes/${courseId}/invitations/${invitationId}/revoke`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return classInvitationViewSchema.parse(await response.json());
}

export async function manageClassMembership(
  accessToken: string,
  courseId: string,
  membershipId: string,
  action: "approve" | "remove",
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<RosterMemberView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/teacher/classes/${courseId}/memberships/${membershipId}`,
    {
      method: "PATCH",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ action }),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return rosterMemberViewSchema.parse(await response.json());
}

export async function fetchTeacherAssignments(
  accessToken: string,
  courseId?: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AssignmentSummaryView[]> {
  const qs = courseId ? `?course_id=${encodeURIComponent(courseId)}` : "";
  const response = await safeFetch(`${baseUrl}/api/v1/teacher/assignments${qs}`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return z.array(assignmentSummaryViewSchema).parse(await response.json());
}

export async function createTeacherAssignment(
  accessToken: string,
  payload: {
    course_id: string;
    title: string;
    instructions_md?: string;
    opens_at?: string | null;
    due_at?: string | null;
    max_marks?: number;
    grading_policy?: GradingPolicy;
    max_attempts?: number;
    allow_ai_hints?: boolean;
    hint_limit?: number;
    allow_late_submissions?: boolean;
    allow_resubmission_on_revision?: boolean;
    publish_now?: boolean;
    problems: Array<{ problem_id: string; points: number }>;
  },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AssignmentSummaryView> {
  const response = await safeFetch(`${baseUrl}/api/v1/teacher/assignments`, {
    method: "POST",
    headers: authHeaders(accessToken, true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return assignmentSummaryViewSchema.parse(await response.json());
}

export async function fetchTeacherAssignmentDetail(
  accessToken: string,
  assignmentId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<TeacherAssignmentDetailView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/teacher/assignments/${assignmentId}`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return teacherAssignmentDetailViewSchema.parse(await response.json());
}

export async function publishTeacherAssignment(
  accessToken: string,
  assignmentId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AssignmentSummaryView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/teacher/assignments/${assignmentId}/publish`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return assignmentSummaryViewSchema.parse(await response.json());
}

export async function archiveTeacherAssignment(
  accessToken: string,
  assignmentId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AssignmentSummaryView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/teacher/assignments/${assignmentId}/archive`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return assignmentSummaryViewSchema.parse(await response.json());
}

export async function gradeStudentSubmission(
  accessToken: string,
  submissionId: string,
  payload: {
    marks_awarded: number;
    action: "save_draft" | "publish" | "request_revision";
    feedback_md: string;
  },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<TeacherSubmissionReviewItem> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/teacher/submissions/${submissionId}/grade`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return teacherSubmissionReviewItemSchema.parse(await response.json());
}

export async function fetchStudentClasses(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<StudentEnrolledCourseView[]> {
  const response = await safeFetch(`${baseUrl}/api/v1/student/classes`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return z.array(studentEnrolledCourseViewSchema).parse(await response.json());
}

export async function joinStudentClass(
  accessToken: string,
  inviteCode: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<StudentEnrolledCourseView> {
  const response = await safeFetch(`${baseUrl}/api/v1/student/classes/join`, {
    method: "POST",
    headers: authHeaders(accessToken, true),
    body: JSON.stringify({ invite_code: inviteCode }),
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return studentEnrolledCourseViewSchema.parse(await response.json());
}

export async function leaveStudentClass(
  accessToken: string,
  courseId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<void> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/student/classes/${courseId}/leave`,
    {
      method: "POST",
      headers: authHeaders(accessToken),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
}

export async function fetchStudentAssignments(
  accessToken: string,
  statusFilter: StudentAssignmentFilter = "all",
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<StudentAssignmentListItemView[]> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/student/assignments?status=${encodeURIComponent(statusFilter)}`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return z
    .array(studentAssignmentListItemViewSchema)
    .parse(await response.json());
}

export async function fetchStudentAssignmentDetail(
  accessToken: string,
  assignmentId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<StudentAssignmentDetailView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/student/assignments/${assignmentId}`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return studentAssignmentDetailViewSchema.parse(await response.json());
}

export async function submitStudentAssignment(
  accessToken: string,
  assignmentId: string,
  payload: {
    problem_id: string;
    language_slug?: string;
    source_code: string;
    student_notes?: string;
    hints_used?: number;
  },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<StudentAssignmentAttemptResponse> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/student/assignments/${assignmentId}/submit`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({
        problem_id: payload.problem_id,
        language_slug: payload.language_slug ?? "python",
        source_code: payload.source_code,
        student_notes: payload.student_notes ?? "",
        hints_used: payload.hints_used ?? 0,
      }),
    },
    EXECUTION_TIMEOUT_MS,
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return studentAssignmentAttemptResponseSchema.parse(await response.json());
}

// =============================================================================
// Phase 8: Advanced Admin Studio, Curriculum Governance, Diagnostics & Audit
// =============================================================================

export async function fetchAdminOverview(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminDashboardOverview> {
  const response = await safeFetch(`${baseUrl}/api/v1/admin/overview`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return adminDashboardOverviewSchema.parse(await response.json());
}

export async function fetchAdminAuditLogs(
  accessToken: string,
  params?: { action_prefix?: string; target_type?: string; limit?: number },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<{ items: AdminAuditLogItem[]; total: number }> {
  const sp = new URLSearchParams();
  if (params?.action_prefix) sp.set("action_prefix", params.action_prefix);
  if (params?.target_type) sp.set("target_type", params.target_type);
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/audit-logs${qs ? `?${qs}` : ""}`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return z
    .object({
      items: z.array(adminAuditLogItemSchema),
      total: z.number().int(),
    })
    .parse(await response.json());
}

export async function submitAdminProblemForReview(
  accessToken: string,
  problemId: string,
  notes: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminProblemDetail> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/problems/${problemId}/submit-review`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ notes }),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return adminProblemDetailSchema.parse(await response.json());
}

export async function rejectAdminProblem(
  accessToken: string,
  problemId: string,
  notes: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminProblemDetail> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/problems/${problemId}/reject`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ notes }),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return adminProblemDetailSchema.parse(await response.json());
}

export async function archiveAdminProblem(
  accessToken: string,
  problemId: string,
  notes: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminProblemArchiveResponse> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/problems/${problemId}/archive`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ notes }),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return adminProblemArchiveResponseSchema.parse(await response.json());
}

export async function fetchAdminProblemVersions(
  accessToken: string,
  problemId: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminProblemVersionsResponse> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/problems/${problemId}/versions`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return adminProblemVersionsResponseSchema.parse(await response.json());
}

export async function fetchAdminTracks(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<LearningTrackView[]> {
  const response = await safeFetch(`${baseUrl}/api/v1/admin/learning/tracks`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return z.array(learningTrackViewSchema).parse(await response.json());
}

export async function updateAdminTrack(
  accessToken: string,
  trackSlug: string,
  payload: {
    title_en: string;
    title_bn: string;
    summary_en: string;
    summary_bn: string;
    recommended_focus_skills: string[];
  },
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<LearningTrackView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/learning/tracks/${trackSlug}`,
    {
      method: "PATCH",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return learningTrackViewSchema.parse(await response.json());
}

export async function fetchAdminLessons(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminLessonDetailView[]> {
  const response = await safeFetch(`${baseUrl}/api/v1/admin/learning/lessons`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return z.array(adminLessonDetailViewSchema).parse(await response.json());
}

export async function upsertAdminLesson(
  accessToken: string,
  payload: Record<string, unknown>,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<LessonSummaryView> {
  const response = await safeFetch(`${baseUrl}/api/v1/admin/learning/lessons`, {
    method: "POST",
    headers: authHeaders(accessToken, true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return lessonSummaryViewSchema.parse(await response.json());
}

export async function updateAdminLessonStatus(
  accessToken: string,
  lessonId: string,
  status: "draft" | "published" | "archived",
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminLessonDetailView> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/learning/lessons/${lessonId}/status`,
    {
      method: "PATCH",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ status }),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return adminLessonDetailViewSchema.parse(await response.json());
}

export async function validateAdminLessonExercise(
  accessToken: string,
  lessonId: string,
  referenceSolution: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminCurriculumValidateResponse> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/learning/lessons/${lessonId}/validate-exercise`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ reference_solution: referenceSolution }),
    },
    EXECUTION_TIMEOUT_MS,
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return adminCurriculumValidateResponseSchema.parse(await response.json());
}

export async function fetchAdminDiagnostics(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminDiagnosticQuestionDetail[]> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/learning/diagnostic-questions`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return z
    .array(adminDiagnosticQuestionDetailSchema)
    .parse(await response.json());
}

export async function createAdminDiagnostic(
  accessToken: string,
  payload: Record<string, unknown>,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<unknown> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/learning/diagnostic-questions`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify(payload),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return response.json();
}

export async function validateAdminDiagnostic(
  accessToken: string,
  questionId: string,
  referenceSolution?: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminCurriculumValidateResponse> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/learning/diagnostic-questions/${questionId}/validate`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ reference_solution: referenceSolution ?? null }),
    },
    EXECUTION_TIMEOUT_MS,
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return adminCurriculumValidateResponseSchema.parse(await response.json());
}

export async function updateAdminDiagnosticStatus(
  accessToken: string,
  questionId: string,
  status: "draft" | "approved" | "published" | "archived",
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminDiagnosticQuestionDetail> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/learning/diagnostic-questions/${questionId}/status`,
    {
      method: "PATCH",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ status }),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return adminDiagnosticQuestionDetailSchema.parse(await response.json());
}

export async function fetchAdminKnowledgeDocs(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<KnowledgeDocumentItem[]> {
  const response = await safeFetch(`${baseUrl}/api/v1/admin/knowledge`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return z.array(knowledgeDocumentSchema).parse(await response.json());
}

export async function upsertAdminKnowledgeDoc(
  accessToken: string,
  payload: Record<string, unknown>,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<KnowledgeDocumentItem> {
  const response = await safeFetch(`${baseUrl}/api/v1/admin/knowledge`, {
    method: "POST",
    headers: authHeaders(accessToken, true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return knowledgeDocumentSchema.parse(await response.json());
}

export async function updateAdminKnowledgeStatus(
  accessToken: string,
  docId: string,
  status: "draft" | "approved" | "archived",
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<KnowledgeDocumentItem> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/knowledge/${docId}/status`,
    {
      method: "PATCH",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ status }),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return knowledgeDocumentSchema.parse(await response.json());
}

export async function fetchAdminUsers(
  accessToken: string,
  limitOrOptions:
    | number
    | { limit?: number; offset?: number; role?: "student" | "teacher" | "admin"; q?: string } = 50,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<{ items: AdminUserSummary[]; total: number }> {
  const opts =
    typeof limitOrOptions === "number"
      ? { limit: limitOrOptions }
      : limitOrOptions;
  const query = new URLSearchParams();
  query.set("limit", String(opts.limit ?? 50));
  if (opts.offset) query.set("offset", String(opts.offset));
  if (opts.role) query.set("role", opts.role);
  if (opts.q?.trim()) query.set("q", opts.q.trim());

  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/users?${query.toString()}`,
    {
      headers: authHeaders(accessToken),
      cache: "no-store",
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return z
    .object({
      items: z.array(adminUserSummarySchema),
      total: z.number().int(),
    })
    .parse(await response.json());
}

export async function grantAdminUserRole(
  accessToken: string,
  userId: string,
  role: "student" | "teacher" | "admin",
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<unknown> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/users/${userId}/roles`,
    {
      method: "POST",
      headers: authHeaders(accessToken, true),
      body: JSON.stringify({ role }),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return response.json();
}

export async function revokeAdminUserRole(
  accessToken: string,
  userId: string,
  role: "student" | "teacher" | "admin",
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<unknown> {
  const response = await safeFetch(
    `${baseUrl}/api/v1/admin/users/${userId}/roles/${role}`,
    {
      method: "DELETE",
      headers: authHeaders(accessToken),
    },
  );
  if (!response.ok) throw await parseErrorResponse(response);
  return response.json();
}

export async function fetchAdminOperationsHealth(
  accessToken: string,
  baseUrl: string = publicEnv.NEXT_PUBLIC_API_BASE_URL,
): Promise<AdminOperationsHealth> {
  const response = await safeFetch(`${baseUrl}/api/v1/admin/operations/health`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });
  if (!response.ok) throw await parseErrorResponse(response);
  return adminOperationsHealthSchema.parse(await response.json());
}
