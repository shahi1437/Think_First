import { z } from "zod";
import { verdictSchema } from "@/types/problems";

export const mentorStateSchema = z.enum([
  "awaiting_submission",
  "diagnosing",
  "asking_question",
  "awaiting_student_response",
  "giving_hint",
  "awaiting_revision",
  "verifying",
  "completed",
  "fallback",
]);

export const providerModeSchema = z.enum(["live_llm", "deterministic_fallback"]);

export const mlCandidateScoreSchema = z.object({
  error_code: z.string(),
  display_name: z.string(),
  probability: z.number(),
});

export const mlDiagnosisResponseSchema = z.object({
  id: z.string().uuid().nullable().optional(),
  submission_id: z.string().uuid().nullable().optional(),
  model_version: z.string(),
  predicted_error_code: z.string(),
  predicted_display_name: z.string(),
  confidence: z.number(),
  is_low_confidence: z.boolean(),
  uncertainty_note: z.string(),
  top_candidates: z.array(mlCandidateScoreSchema),
});

export const ragCitationSchema = z.object({
  chunk_id: z.string().uuid(),
  document_id: z.string().uuid(),
  document_slug: z.string(),
  source_title: z.string(),
  source_name: z.string(),
  source_version: z.string(),
  topic: z.string(),
  heading: z.string(),
  excerpt: z.string(),
  similarity: z.number(),
});

export const mentorTurnViewSchema = z.object({
  id: z.string().uuid(),
  turn_index: z.number().int(),
  role: z.enum(["student", "mentor", "system"]),
  state_after: mentorStateSchema,
  message_text: z.string(),
  structured_payload: z.record(z.string(), z.unknown()),
  citations: z.array(ragCitationSchema).default([]),
  provider_mode: providerModeSchema,
  created_at: z.string(),
});

export const mentorSessionDetailSchema = z.object({
  id: z.string().uuid(),
  problem_id: z.string().uuid(),
  problem_version_id: z.string().uuid(),
  latest_submission_id: z.string().uuid().nullable().optional(),
  current_state: mentorStateSchema,
  explanation_language: z.enum(["en", "bn"]),
  learner_level: z.string(),
  hints_used: z.number().int(),
  max_hints: z.number().int(),
  provider_mode: providerModeSchema,
  latest_diagnosis: mlDiagnosisResponseSchema.nullable().optional(),
  latest_citations: z.array(ragCitationSchema).default([]),
  turns: z.array(mentorTurnViewSchema).default([]),
  transfer_unlocked: z.boolean().default(false),
  verification_link_id: z.string().uuid().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const verificationAttemptViewSchema = z.object({
  id: z.string().uuid(),
  verification_link_id: z.string().uuid(),
  transfer_problem_id: z.string().uuid(),
  transfer_submission_id: z.string().uuid().nullable().optional(),
  hints_used: z.number().int(),
  student_explanation: z.string(),
  outcome: z.enum([
    "in_progress",
    "verified_independent",
    "attempted_not_verified",
  ]),
  verdict: verdictSchema,
  passed_tests: z.number().int(),
  total_tests: z.number().int(),
  summary_message: z.string(),
  created_at: z.string(),
});

export const transferChallengeSummarySchema = z.object({
  verification_link_id: z.string().uuid(),
  source_problem_id: z.string().uuid(),
  transfer_problem_id: z.string().uuid(),
  transfer_problem_title: z.string(),
  transfer_problem_slug: z.string(),
  skill_focus: z.string(),
  max_hints_allowed: z.number().int(),
  instructions_md: z.string(),
  unlocked: z.boolean(),
  unlock_reason: z.string(),
  latest_attempt: verificationAttemptViewSchema.nullable().optional(),
});

export const learningEventViewSchema = z.object({
  id: z.string().uuid(),
  problem_id: z.string().uuid().nullable().optional(),
  submission_id: z.string().uuid().nullable().optional(),
  diagnosis_id: z.string().uuid().nullable().optional(),
  event_type: z.string(),
  hints_used: z.number().int(),
  verdict: z.string().nullable().optional(),
  verification_outcome: z.string().nullable().optional(),
  metadata: z.record(z.string(), z.unknown()),
  created_at: z.string(),
});

export type MentorState = z.infer<typeof mentorStateSchema>;
export type ProviderMode = z.infer<typeof providerModeSchema>;
export type MLDiagnosisResponse = z.infer<typeof mlDiagnosisResponseSchema>;
export type RagCitation = z.infer<typeof ragCitationSchema>;
export type MentorTurnView = z.infer<typeof mentorTurnViewSchema>;
export type MentorSessionDetail = z.infer<typeof mentorSessionDetailSchema>;
export type VerificationAttemptView = z.infer<
  typeof verificationAttemptViewSchema
>;
export type TransferChallengeSummary = z.infer<
  typeof transferChallengeSummarySchema
>;
export type LearningEventView = z.infer<typeof learningEventViewSchema>;
