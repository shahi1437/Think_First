import { z } from "zod";
import {
  diagnosticDomainSchema,
  diagnosticOptionViewSchema,
  lessonExerciseTestCaseSchema,
  lessonGuidedExerciseSchema,
  lessonInteractiveExampleSchema,
  trackSlugSchema,
} from "@/types/learning";
import { difficultySchema, problemModeSchema } from "@/types/problems";

export const adminAuditLogItemSchema = z.object({
  id: z.string(),
  actor_user_id: z.string().nullable().optional(),
  actor_email: z.string().nullable().optional(),
  actor_name: z.string().nullable().optional(),
  action: z.string(),
  target_type: z.string(),
  target_id: z.string(),
  metadata: z.record(z.string(), z.unknown()).default({}),
  request_id: z.string().nullable().optional(),
  created_at: z.string(),
});

export const adminReviewQueueItemSchema = z.object({
  problem_id: z.string(),
  version_id: z.string(),
  slug: z.string(),
  title: z.string(),
  difficulty: difficultySchema,
  mode: problemModeSchema,
  status: z.string(),
  version_number: z.number().int(),
  updated_at: z.string(),
});

export const adminTrackCoverageItemSchema = z.object({
  track_slug: trackSlugSchema,
  title_en: z.string(),
  title_bn: z.string(),
  lesson_count: z.number().int(),
  problem_count: z.number().int(),
  focus_skills: z.array(z.string()),
});

export const adminDashboardOverviewSchema = z.object({
  problems_total: z.number().int(),
  problems_published: z.number().int(),
  problems_draft: z.number().int(),
  problems_validated: z.number().int(),
  problems_in_review: z.number().int(),
  problems_approved: z.number().int(),
  problems_archived: z.number().int(),
  problems_intermediate_or_advanced: z.number().int(),
  lessons_published: z.number().int(),
  lessons_total: z.number().int(),
  diagnostic_published: z.number().int(),
  diagnostic_stretch_count: z.number().int(),
  knowledge_approved: z.number().int(),
  knowledge_total: z.number().int(),
  skill_nodes_count: z.number().int(),
  students_count: z.number().int().optional(),
  teachers_count: z.number().int().optional(),
  admins_count: z.number().int().optional(),
  courses_total: z.number().int().optional(),
  courses_active: z.number().int().optional(),
  enrollments_active: z.number().int().optional(),
  assignments_published: z.number().int().optional(),
  review_queue: z.array(adminReviewQueueItemSchema),
  track_coverage: z.array(adminTrackCoverageItemSchema),
  recent_audit_logs: z.array(adminAuditLogItemSchema),
});

export const adminLessonDetailViewSchema = z.object({
  lesson_id: z.string(),
  version_id: z.string(),
  version_number: z.number().int(),
  slug: z.string(),
  language_slug: z.string().optional(),
  skill_slug: z.string(),
  display_order: z.number().int(),
  status: z.string(),
  is_published_current: z.boolean(),
  title_en: z.string(),
  title_bn: z.string(),
  summary_en: z.string(),
  summary_bn: z.string(),
  content_en_md: z.string(),
  content_bn_md: z.string(),
  learning_objectives: z.array(z.string()),
  prerequisite_lesson_slugs: z.array(z.string()),
  track_slugs: z.array(z.string()),
  interactive_examples: z.array(lessonInteractiveExampleSchema),
  guided_exercise: lessonGuidedExerciseSchema,
  estimated_minutes: z.number().int(),
  published_at: z.string().nullable().optional(),
  updated_at: z.string(),
});

export const adminCurriculumValidateResponseSchema = z.object({
  target_type: z.string(),
  target_id: z.string(),
  passed: z.boolean(),
  passed_tests: z.number().int(),
  total_tests: z.number().int(),
  errors: z.array(z.string()).default([]),
  warnings: z.array(z.string()).default([]),
});

export const adminDiagnosticQuestionDetailSchema = z.object({
  id: z.string(),
  slug: z.string(),
  domain_slug: diagnosticDomainSchema,
  skill_slug: z.string(),
  difficulty: z.enum(["foundation", "core", "stretch"]),
  question_type: z.enum(["mcq", "code_execution"]),
  prompt_en: z.string(),
  prompt_bn: z.string(),
  code_snippet: z.string().nullable().optional(),
  options: z.array(diagnosticOptionViewSchema),
  starter_code: z.string().nullable().optional(),
  language_slug: z.string(),
  status: z.string(),
  correct_option_id: z.string().nullable().optional(),
  explanation_en: z.string(),
  explanation_bn: z.string(),
  evaluation_tests: z.array(lessonExerciseTestCaseSchema),
  reference_solution: z.string().nullable().optional(),
  validation_summary: z.record(z.string(), z.unknown()).default({}),
  published_at: z.string().nullable().optional(),
  updated_at: z.string(),
});

export const knowledgeDocumentSchema = z.object({
  id: z.string(),
  slug: z.string(),
  title: z.string(),
  language_slug: z.string(),
  topic: z.string(),
  error_codes: z.array(z.string()),
  source_name: z.string(),
  source_version: z.string(),
  status: z.enum(["draft", "approved", "archived"]),
  chunk_count: z.number().int(),
  approved_at: z.string().nullable().optional(),
  updated_at: z.string(),
});

export const adminUserSummarySchema = z.object({
  id: z.string(),
  email: z.string(),
  full_name: z.string().nullable().optional(),
  roles: z.array(z.string()),
  onboarding_completed: z.boolean(),
  created_at: z.string(),
});

export const operationalCheckStatusSchema = z.object({
  name: z.string(),
  status: z.enum(["ok", "degraded", "unavailable"]),
  latency_ms: z.number().nullable().optional(),
  detail: z.string(),
});

export const adminOperationsHealthSchema = z.object({
  overall_status: z.enum(["ok", "degraded"]),
  environment: z.string(),
  rate_limit_enabled: z.boolean(),
  llm_provider_mode: z.enum(["live_llm", "deterministic_fallback"]),
  llm_provider: z.string(),
  llm_model: z.string(),
  checks: z.array(operationalCheckStatusSchema),
});

export const teacherInvitationStatusSchema = z.enum([
  "pending",
  "accepted",
  "revoked",
  "expired",
]);

export const teacherInvitationDeliveryStatusSchema = z.enum([
  "sent",
  "delivery_blocked",
]);

export const teacherStatusKindSchema = z.enum([
  "active_teacher",
  "existing_user_not_teacher",
  "pending_invitation",
  "expired_invitation",
  "revoked_invitation",
  "not_found",
]);

export const teacherInvitationViewSchema = z.object({
  id: z.string(),
  email: z.string(),
  full_name: z.string().default(""),
  status: teacherInvitationStatusSchema,
  delivery_status: teacherInvitationDeliveryStatusSchema,
  delivery_detail: z.string(),
  token_preview: z.string(),
  invited_by_id: z.string().nullable().optional(),
  invited_by_email: z.string().nullable().optional(),
  accepted_by_user_id: z.string().nullable().optional(),
  accepted_at: z.string().nullable().optional(),
  revoked_by_user_id: z.string().nullable().optional(),
  revoked_at: z.string().nullable().optional(),
  resend_count: z.number().int().default(0),
  expires_at: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const teacherInvitationMutationResponseSchema = z.object({
  invitation: teacherInvitationViewSchema,
  invitation_token: z.string().nullable().optional(),
  accept_path: z.string().nullable().optional(),
  action: z.enum([
    "teacher.invitation_created",
    "teacher.invitation_resent",
    "teacher.invitation_revoked",
  ]),
});

export const teacherLookupResponseSchema = z.object({
  email: z.string(),
  status: teacherStatusKindSchema,
  can_grant_directly: z.boolean(),
  can_invite: z.boolean(),
  existing_user: adminUserSummarySchema.nullable().optional(),
  latest_invitation: teacherInvitationViewSchema.nullable().optional(),
  message: z.string(),
});

export const teacherManagementOverviewSchema = z.object({
  active_teachers: z.array(adminUserSummarySchema),
  active_teachers_total: z.number().int(),
  invitations: z.array(teacherInvitationViewSchema),
  invitations_total: z.number().int().optional(),
  invitations_limit: z.number().int().optional(),
  invitations_offset: z.number().int().optional(),
  pending_invitations_count: z.number().int(),
});

export const teacherInvitationInspectResponseSchema = z.object({
  invitation_id: z.string(),
  email: z.string(),
  full_name: z.string().default(""),
  status: teacherInvitationStatusSchema,
  expires_at: z.string(),
  is_valid: z.boolean(),
  message: z.string(),
});

export type AdminAuditLogItem = z.infer<typeof adminAuditLogItemSchema>;
export type AdminDashboardOverview = z.infer<typeof adminDashboardOverviewSchema>;
export type AdminOperationsHealth = z.infer<typeof adminOperationsHealthSchema>;
export type AdminLessonDetailView = z.infer<typeof adminLessonDetailViewSchema>;
export type AdminCurriculumValidateResponse = z.infer<
  typeof adminCurriculumValidateResponseSchema
>;
export type AdminDiagnosticQuestionDetail = z.infer<
  typeof adminDiagnosticQuestionDetailSchema
>;
export type KnowledgeDocumentItem = z.infer<typeof knowledgeDocumentSchema>;
export type AdminUserSummary = z.infer<typeof adminUserSummarySchema>;
export type TeacherInvitationStatus = z.infer<
  typeof teacherInvitationStatusSchema
>;
export type TeacherInvitationDeliveryStatus = z.infer<
  typeof teacherInvitationDeliveryStatusSchema
>;
export type TeacherStatusKind = z.infer<typeof teacherStatusKindSchema>;
export type TeacherInvitationView = z.infer<typeof teacherInvitationViewSchema>;
export type TeacherInvitationMutationResponse = z.infer<
  typeof teacherInvitationMutationResponseSchema
>;
export type TeacherLookupResponse = z.infer<typeof teacherLookupResponseSchema>;
export type TeacherManagementOverview = z.infer<
  typeof teacherManagementOverviewSchema
>;
export type TeacherInvitationInspectResponse = z.infer<
  typeof teacherInvitationInspectResponseSchema
>;
