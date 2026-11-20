import { z } from "zod";

export const trackSlugSchema = z.enum([
  "absolute_beginner",
  "basic_university",
  "intermediate",
  "advanced",
]);

export const skillStateSchema = z.enum([
  "unobserved",
  "introduced",
  "guided",
  "independent",
  "transferred",
  "retained",
]);

export const diagnosticDomainSchema = z.enum([
  "variables",
  "syntax_runtime_debugging",
  "conditions",
  "loop_boundaries",
  "arrays_lists",
  "indexing",
  "functions",
  "mixed_logic",
]);

export const learningTrackViewSchema = z.object({
  slug: trackSlugSchema,
  title_en: z.string(),
  title_bn: z.string(),
  summary_en: z.string(),
  summary_bn: z.string(),
  target_audience_en: z.string(),
  target_audience_bn: z.string(),
  display_order: z.number().int(),
  recommended_focus_skills: z.array(z.string()),
});

export const studentTrackStatusSchema = z.object({
  selected_track_slug: trackSlugSchema,
  recommended_track_slug: trackSlugSchema.nullable().optional(),
  recommendation_source: z.enum([
    "onboarding_initial",
    "diagnostic_evidence",
    "manual_selection",
  ]),
  recommendation_reason: z.string(),
  diagnostic_completed: z.boolean(),
  tracks: z.array(learningTrackViewSchema),
});

export const lessonInteractiveExampleSchema = z.object({
  title: z.string(),
  code: z.string(),
  input_data: z.string().default(""),
  expected_output: z.string(),
  explanation_en: z.string(),
  explanation_bn: z.string(),
});

export const lessonExerciseTestCaseSchema = z.object({
  name: z.string(),
  input_data: z.string(),
  expected_output: z.string(),
});

export const lessonGuidedExerciseSchema = z.object({
  prompt_en: z.string(),
  prompt_bn: z.string(),
  language_slug: z.string().default("python"),
  starter_code: z.string(),
  test_cases: z.array(lessonExerciseTestCaseSchema).default([]),
});

export const lessonSummaryViewSchema = z.object({
  lesson_id: z.string().uuid(),
  version_id: z.string().uuid(),
  slug: z.string(),
  skill_slug: z.string(),
  display_order: z.number().int(),
  title_en: z.string(),
  title_bn: z.string(),
  summary_en: z.string(),
  summary_bn: z.string(),
  prerequisite_lesson_slugs: z.array(z.string()),
  track_slugs: z.array(z.string()),
  estimated_minutes: z.number().int(),
  progress_status: z.enum(["not_started", "in_progress", "completed"]),
  reading_completed: z.boolean(),
  exercise_passed: z.boolean(),
  exercise_attempts: z.number().int(),
  prerequisites_met: z.boolean(),
});

export const lessonDetailViewSchema = lessonSummaryViewSchema.extend({
  content_en_md: z.string(),
  content_bn_md: z.string(),
  learning_objectives: z.array(z.string()),
  interactive_examples: z.array(lessonInteractiveExampleSchema),
  guided_exercise: lessonGuidedExerciseSchema,
  last_code: z.string().nullable().optional(),
  last_verdict: z.string().nullable().optional(),
  last_stdout: z.string().nullable().optional(),
  last_stderr: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
});

export const lessonExerciseCaseResultSchema = z.object({
  name: z.string(),
  input_data: z.string(),
  expected_output: z.string(),
  actual_output: z.string().nullable().optional(),
  stderr: z.string().nullable().optional(),
  compile_output: z.string().nullable().optional(),
  verdict: z.string(),
  passed: z.boolean(),
});

export const lessonExerciseRunResponseSchema = z.object({
  lesson_id: z.string().uuid(),
  verdict: z.string(),
  passed_tests: z.number().int(),
  total_tests: z.number().int(),
  exercise_passed: z.boolean(),
  progress_status: z.enum(["not_started", "in_progress", "completed"]),
  skill_state_after: skillStateSchema,
  case_results: z.array(lessonExerciseCaseResultSchema),
});

export const diagnosticOptionViewSchema = z.object({
  id: z.string(),
  text_en: z.string(),
  text_bn: z.string(),
});

export const diagnosticQuestionPublicViewSchema = z.object({
  id: z.string().uuid(),
  slug: z.string(),
  domain_slug: diagnosticDomainSchema,
  skill_slug: z.string(),
  difficulty: z.enum(["foundation", "core", "stretch"]),
  question_type: z.enum(["mcq", "code_execution"]),
  prompt_en: z.string(),
  prompt_bn: z.string(),
  code_snippet: z.string().nullable().optional(),
  options: z.array(diagnosticOptionViewSchema).default([]),
  starter_code: z.string().nullable().optional(),
  language_slug: z.string().default("python"),
});

export const diagnosticDomainEvidenceSchema = z.object({
  domain_slug: diagnosticDomainSchema,
  observed_attempts: z.number().int(),
  observed_correct: z.number().int(),
  execution_verified: z.boolean(),
  evidence_status: z.enum([
    "insufficient_evidence",
    "gap_detected",
    "guided_needed",
    "demonstrated_basic",
    "demonstrated_strong",
  ]),
  note_en: z.string(),
  note_bn: z.string(),
});

export const diagnosticResponseFeedbackSchema = z.object({
  question_id: z.string().uuid(),
  domain_slug: diagnosticDomainSchema,
  difficulty: z.enum(["foundation", "core", "stretch"]),
  question_type: z.enum(["mcq", "code_execution"]),
  is_correct: z.boolean(),
  execution_verdict: z.string().nullable().optional(),
  passed_tests: z.number().int(),
  total_tests: z.number().int(),
  execution_stderr: z.string().nullable().optional(),
  feedback_en: z.string(),
  feedback_bn: z.string(),
  adaptive_action: z.string().nullable().optional(),
});

export const diagnosticSessionViewSchema = z.object({
  id: z.string().uuid(),
  status: z.enum(["in_progress", "completed", "abandoned"]),
  explanation_language: z.enum(["en", "bn"]),
  answered_count: z.number().int(),
  remaining_count: z.number().int(),
  adaptive_followups_added: z.number().int(),
  current_question: diagnosticQuestionPublicViewSchema.nullable().optional(),
  last_feedback: diagnosticResponseFeedbackSchema.nullable().optional(),
  recommended_track_slug: trackSlugSchema.nullable().optional(),
  recommendation_rationale: z.string().nullable().optional(),
  domain_evidence: z.array(diagnosticDomainEvidenceSchema).default([]),
  started_at: z.string(),
  completed_at: z.string().nullable().optional(),
});

export const skillNodeStateViewSchema = z.object({
  slug: z.string(),
  title_en: z.string(),
  title_bn: z.string(),
  description_en: z.string(),
  description_bn: z.string(),
  domain_slug: z.string(),
  tier: z.number().int(),
  display_order: z.number().int(),
  prerequisites: z.array(z.string()),
  state: skillStateSchema,
  evidence_count: z.number().int(),
  uncertainty_note: z.string(),
  last_evidence_type: z.string().nullable().optional(),
  last_evidence_at: z.string().nullable().optional(),
});

export const skillTransitionViewSchema = z.object({
  id: z.string().uuid(),
  skill_slug: z.string(),
  from_state: z.string(),
  to_state: z.string(),
  evidence_source: z.string(),
  reason: z.string(),
  created_at: z.string(),
});

export const skillGraphViewSchema = z.object({
  nodes: z.array(skillNodeStateViewSchema),
  recent_transitions: z.array(skillTransitionViewSchema),
  state_legend: z.array(z.record(z.string(), z.string())),
});

export const recommendationItemViewSchema = z.object({
  recommendation_type: z.enum([
    "diagnostic_assessment",
    "lesson",
    "problem",
    "transfer_challenge",
  ]),
  target_id: z.string(),
  target_slug: z.string(),
  title: z.string(),
  priority: z.number().int(),
  reason_en: z.string(),
  reason_bn: z.string(),
  evidence_factors: z.array(z.string()),
  href: z.string(),
});

export const learningDashboardViewSchema = z.object({
  track_status: studentTrackStatusSchema,
  lessons_completed: z.number().int(),
  lessons_total: z.number().int(),
  diagnostic_sessions_completed: z.number().int(),
  latest_diagnostic: diagnosticSessionViewSchema.nullable().optional(),
  skill_graph: skillGraphViewSchema,
  recommendations: z.array(recommendationItemViewSchema),
});

export type TrackSlug = z.infer<typeof trackSlugSchema>;
export type SkillState = z.infer<typeof skillStateSchema>;
export type LearningTrackView = z.infer<typeof learningTrackViewSchema>;
export type StudentTrackStatus = z.infer<typeof studentTrackStatusSchema>;
export type LessonSummaryView = z.infer<typeof lessonSummaryViewSchema>;
export type LessonDetailView = z.infer<typeof lessonDetailViewSchema>;
export type LessonExerciseRunResponse = z.infer<
  typeof lessonExerciseRunResponseSchema
>;
export type DiagnosticSessionView = z.infer<typeof diagnosticSessionViewSchema>;
export type SkillGraphView = z.infer<typeof skillGraphViewSchema>;
export type RecommendationItemView = z.infer<
  typeof recommendationItemViewSchema
>;
export type LearningDashboardView = z.infer<typeof learningDashboardViewSchema>;
