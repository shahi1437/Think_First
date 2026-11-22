import { z } from "zod";

export const dnaDimensionKeySchema = z.enum([
  "tracing",
  "coding",
  "debugging",
  "testing",
  "transfer",
  "retention",
]);
export type DnaDimensionKey = z.infer<typeof dnaDimensionKeySchema>;

export const dnaEvidenceBandSchema = z.enum([
  "unobserved",
  "emerging",
  "developing",
  "verified",
]);
export type DnaEvidenceBand = z.infer<typeof dnaEvidenceBandSchema>;

export const dailyTaskTypeSchema = z.enum([
  "diagnostic",
  "lesson",
  "problem",
  "debugging",
  "transfer",
  "retention",
]);
export type DailyTaskType = z.infer<typeof dailyTaskTypeSchema>;

export const dailyTaskStatusSchema = z.enum([
  "pending",
  "completed",
  "skipped",
]);
export type DailyTaskStatus = z.infer<typeof dailyTaskStatusSchema>;

export const historyCategorySchema = z.enum([
  "lesson",
  "diagnostic",
  "submission",
  "revision",
  "mentor",
  "hint",
  "transfer",
  "skill",
  "daily_plan",
  "retention",
]);
export type HistoryCategory = z.infer<typeof historyCategorySchema>;

export const retentionScheduleStatusSchema = z.enum([
  "scheduled",
  "due",
  "passed_retained",
  "needs_review",
]);
export type RetentionScheduleStatus = z.infer<
  typeof retentionScheduleStatusSchema
>;

export const retentionOutcomeSchema = z.enum([
  "retained_verified",
  "passed_too_early",
  "needs_review",
]);
export type RetentionOutcome = z.infer<typeof retentionOutcomeSchema>;

export const learningDnaDimensionViewSchema = z.object({
  dimension: dnaDimensionKeySchema,
  label_en: z.string(),
  label_bn: z.string(),
  evidence_band: dnaEvidenceBandSchema,
  evidence_count: z.number(),
  factual_metrics: z.record(
    z.string(),
    z.union([z.number(), z.string()]),
  ),
  summary_en: z.string(),
  summary_bn: z.string(),
  uncertainty_note: z.string(),
});
export type LearningDnaDimensionView = z.infer<
  typeof learningDnaDimensionViewSchema
>;

export const learningDnaSnapshotSummarySchema = z.object({
  id: z.string(),
  selected_track_slug: z.string(),
  computed_at: z.string(),
  strengths: z.array(z.string()),
  growth_areas: z.array(z.string()),
});

export const learningDnaProfileViewSchema = z.object({
  snapshot_id: z.string(),
  language_slug: z.string().optional(),
  computed_at: z.string(),
  selected_track_slug: z.string(),
  dimensions: z.array(learningDnaDimensionViewSchema),
  skill_state_summary: z.record(z.string(), z.number()),
  strengths: z.array(z.string()),
  growth_areas: z.array(z.string()),
  source_counts: z.record(z.string(), z.number()),
  methodology_note_en: z.string(),
  methodology_note_bn: z.string(),
  recent_snapshots: z.array(learningDnaSnapshotSummarySchema),
});
export type LearningDnaProfileView = z.infer<
  typeof learningDnaProfileViewSchema
>;

export const dailyPlanTaskViewSchema = z.object({
  id: z.string(),
  task_order: z.number(),
  task_type: dailyTaskTypeSchema,
  skill_slug: z.string().nullable(),
  target_id: z.string(),
  target_slug: z.string(),
  title_en: z.string(),
  title_bn: z.string(),
  reason_en: z.string(),
  reason_bn: z.string(),
  href: z.string(),
  estimated_minutes: z.number(),
  status: dailyTaskStatusSchema,
  completed_at: z.string().nullable(),
  completion_evidence_ref: z.string().nullable(),
});
export type DailyPlanTaskView = z.infer<typeof dailyPlanTaskViewSchema>;

export const dailyLearningPlanViewSchema = z.object({
  id: z.string(),
  language_slug: z.string().optional(),
  plan_date: z.string(),
  version_number: z.number(),
  is_active: z.boolean(),
  selected_track_slug: z.string(),
  available_minutes: z.number(),
  total_estimated_minutes: z.number(),
  completed_tasks: z.number(),
  total_tasks: z.number(),
  generation_reason_en: z.string(),
  generation_reason_bn: z.string(),
  tasks: z.array(dailyPlanTaskViewSchema),
  created_at: z.string(),
  updated_at: z.string(),
});
export type DailyLearningPlanView = z.infer<typeof dailyLearningPlanViewSchema>;

export const dailyPlanHistoryItemSchema = z.object({
  id: z.string(),
  plan_date: z.string(),
  version_number: z.number(),
  is_active: z.boolean(),
  available_minutes: z.number(),
  total_estimated_minutes: z.number(),
  completed_tasks: z.number(),
  total_tasks: z.number(),
  created_at: z.string(),
});

export const dailyPlanWorkspaceViewSchema = z.object({
  active_plan: dailyLearningPlanViewSchema,
  history: z.array(dailyPlanHistoryItemSchema),
});
export type DailyPlanWorkspaceView = z.infer<
  typeof dailyPlanWorkspaceViewSchema
>;

export const learningHistoryItemViewSchema = z.object({
  id: z.string(),
  category: historyCategorySchema,
  title_en: z.string(),
  title_bn: z.string(),
  summary_en: z.string(),
  summary_bn: z.string(),
  verdict_or_status: z.string().nullable(),
  skill_slug: z.string().nullable(),
  href: z.string().nullable(),
  metadata: z.record(z.string(), z.unknown()),
  occurred_at: z.string(),
});
export type LearningHistoryItemView = z.infer<
  typeof learningHistoryItemViewSchema
>;

export const learningHistoryResponseViewSchema = z.object({
  items: z.array(learningHistoryItemViewSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
  category_counts: z.record(z.string(), z.number()),
});
export type LearningHistoryResponseView = z.infer<
  typeof learningHistoryResponseViewSchema
>;

export const retentionScheduleViewSchema = z.object({
  id: z.string(),
  language_slug: z.string().optional(),
  skill_slug: z.string(),
  skill_title_en: z.string(),
  skill_title_bn: z.string(),
  problem_id: z.string(),
  problem_slug: z.string(),
  problem_title: z.string(),
  starter_code: z.string(),
  source_evidence_type: z.string(),
  source_verified_at: z.string(),
  due_at: z.string(),
  interval_hours: z.number(),
  status: retentionScheduleStatusSchema,
  is_due_now: z.boolean(),
  hours_until_eligible: z.number(),
  last_attempt_at: z.string().nullable(),
  created_at: z.string(),
});
export type RetentionScheduleView = z.infer<typeof retentionScheduleViewSchema>;

export const retentionAttemptViewSchema = z.object({
  id: z.string(),
  schedule_id: z.string(),
  skill_slug: z.string(),
  problem_id: z.string(),
  submission_id: z.string().nullable(),
  language_slug: z.string(),
  verdict: z.string(),
  passed_tests: z.number(),
  total_tests: z.number(),
  elapsed_hours_since_initial: z.number(),
  outcome: retentionOutcomeSchema,
  summary_message: z.string(),
  created_at: z.string(),
});
export type RetentionAttemptView = z.infer<typeof retentionAttemptViewSchema>;

export const retentionOverviewViewSchema = z.object({
  schedules: z.array(retentionScheduleViewSchema),
  recent_attempts: z.array(retentionAttemptViewSchema),
  due_count: z.number(),
  retained_skills_count: z.number(),
  policy_note_en: z.string(),
  policy_note_bn: z.string(),
});
export type RetentionOverviewView = z.infer<typeof retentionOverviewViewSchema>;
