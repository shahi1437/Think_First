import { z } from "zod";

export const difficultySchema = z.enum([
  "beginner",
  "basic",
  "intermediate",
  "advanced",
]);
export const problemModeSchema = z.enum(["coding", "debugging"]);
export const problemStatusSchema = z.enum([
  "draft",
  "validated",
  "in_review",
  "approved",
  "published",
  "archived",
]);
export const verdictSchema = z.enum([
  "pending",
  "accepted",
  "wrong_answer",
  "compilation_error",
  "runtime_error",
  "time_limit_exceeded",
  "memory_limit_exceeded",
  "internal_error",
]);

export const languageItemSchema = z.object({
  slug: z.string(),
  display_name: z.string(),
  judge0_language_id: z.number().int(),
  monaco_language: z.string(),
  version_label: z.string(),
  is_enabled: z.boolean(),
});

export const problemExampleSchema = z.object({
  input: z.string(),
  output: z.string(),
  explanation: z.string().default(""),
});

export const publicTestCaseSchema = z.object({
  id: z.string(),
  ordinal: z.number().int(),
  name: z.string(),
  input_data: z.string(),
  expected_output: z.string(),
});

export const studentVariantSchema = z.object({
  language_slug: z.string(),
  display_name: z.string(),
  monaco_language: z.string(),
  starter_code: z.string(),
  buggy_starter_code: z.string().nullable().optional(),
  debugging_prompt: z.string().nullable().optional(),
});

export const studentProblemListItemSchema = z.object({
  problem_id: z.string(),
  version_id: z.string(),
  slug: z.string(),
  title: z.string(),
  difficulty: difficultySchema,
  track_slug: z.string().nullable().optional(),
  mode: problemModeSchema,
  topics: z.array(z.string()),
  skills: z.array(z.string()),
  supported_languages: z.array(z.string()),
  published_at: z.string().nullable().optional(),
});

export const paginatedProblemsSchema = z.object({
  items: z.array(studentProblemListItemSchema),
  total: z.number().int(),
  limit: z.number().int(),
  offset: z.number().int(),
});

export const studentProblemDetailSchema = z.object({
  problem_id: z.string(),
  version_id: z.string(),
  version_number: z.number().int(),
  slug: z.string(),
  title: z.string(),
  statement_md: z.string(),
  difficulty: difficultySchema,
  track_slug: z.string().nullable().optional(),
  mode: problemModeSchema,
  topics: z.array(z.string()),
  skills: z.array(z.string()),
  prerequisites: z.array(z.string()),
  learning_objectives: z.array(z.string()),
  examples: z.array(problemExampleSchema),
  time_limit_ms: z.number().int(),
  memory_limit_kb: z.number().int(),
  variants: z.array(studentVariantSchema),
  public_test_cases: z.array(publicTestCaseSchema),
  hidden_test_count: z.number().int(),
});

export const testCaseExecutionViewSchema = z.object({
  ordinal: z.number().int(),
  name: z.string(),
  is_hidden: z.boolean(),
  verdict: verdictSchema,
  input_data: z.string().nullable().optional(),
  expected_output: z.string().nullable().optional(),
  stdout: z.string().nullable().optional(),
  stderr: z.string().nullable().optional(),
  compile_output: z.string().nullable().optional(),
  runtime_ms: z.number().int().nullable().optional(),
  memory_kb: z.number().int().nullable().optional(),
});

export const submissionResponseSchema = z.object({
  id: z.string(),
  problem_id: z.string(),
  problem_version_id: z.string(),
  language_slug: z.string(),
  submission_kind: z.enum(["run", "submit"]),
  source_code: z.string(),
  prediction_text: z.string().nullable().optional(),
  explanation_text: z.string().nullable().optional(),
  status: z.enum(["queued", "running", "completed", "failed"]),
  verdict: verdictSchema,
  passed_tests: z.number().int(),
  total_tests: z.number().int(),
  runtime_ms: z.number().int().nullable().optional(),
  memory_kb: z.number().int().nullable().optional(),
  execution_provider: z.string().optional(),
  execution_evidence: z.record(z.string(), z.unknown()),
  results: z.array(testCaseExecutionViewSchema),
  created_at: z.string(),
});

export const submissionSummaryItemSchema = z.object({
  id: z.string(),
  problem_id: z.string(),
  problem_version_id: z.string(),
  language_slug: z.string(),
  submission_kind: z.enum(["run", "submit"]),
  status: z.enum(["queued", "running", "completed", "failed"]),
  verdict: verdictSchema,
  passed_tests: z.number().int(),
  total_tests: z.number().int(),
  runtime_ms: z.number().int().nullable().optional(),
  memory_kb: z.number().int().nullable().optional(),
  execution_provider: z.string().optional(),
  created_at: z.string(),
});

export const paginatedSubmissionsSchema = z.object({
  items: z.array(submissionSummaryItemSchema),
  total: z.number().int(),
  limit: z.number().int(),
  offset: z.number().int(),
});

export const executionAvailabilitySchema = z.object({
  mode: z.enum(["direct_judge0", "worker_queue", "disabled"]),
  available: z.boolean(),
  worker_online: z.boolean(),
  active_workers: z.number().int(),
  queue_depth: z.number().int(),
  last_heartbeat_at: z.string().nullable().optional(),
  message: z.string(),
});

export const revisionResponseSchema = z.object({
  id: z.string(),
  problem_version_id: z.string(),
  language_slug: z.string(),
  source_code: z.string(),
  prediction_text: z.string().nullable().optional(),
  explanation_text: z.string().nullable().optional(),
  revision_type: z.enum(["autosave", "manual", "run", "submit"]),
  created_at: z.string(),
});

// Admin Problem Studio Schemas
export const adminProblemListItemSchema = z.object({
  problem_id: z.string(),
  slug: z.string(),
  latest_version_id: z.string(),
  latest_version_number: z.number().int(),
  title: z.string(),
  difficulty: difficultySchema,
  track_slug: z.string().nullable().optional(),
  mode: problemModeSchema,
  status: problemStatusSchema,
  topics: z.array(z.string()),
  is_published: z.boolean(),
  is_archived: z.boolean().default(false),
  updated_at: z.string(),
});

export const paginatedAdminProblemsSchema = z.object({
  items: z.array(adminProblemListItemSchema),
  total: z.number().int(),
  limit: z.number().int(),
  offset: z.number().int(),
});

export const adminVariantDetailSchema = z.object({
  id: z.string(),
  language_slug: z.string(),
  starter_code: z.string(),
  buggy_starter_code: z.string().nullable().optional(),
  debugging_prompt: z.string().nullable().optional(),
  reference_solution: z.string(),
  expected_bug_summary: z.string().nullable().optional(),
  expected_failure_category: z.string().nullable().optional(),
});

export const adminTestCaseDetailSchema = z.object({
  id: z.string(),
  ordinal: z.number().int(),
  name: z.string(),
  input_data: z.string(),
  expected_output: z.string(),
  is_hidden: z.boolean(),
  weight: z.number().int(),
});

export const adminContentReviewItemSchema = z.object({
  id: z.string(),
  action: z.string(),
  notes: z.string(),
  validation_summary: z.record(z.string(), z.unknown()),
  created_at: z.string(),
});

export const adminProblemDetailSchema = z.object({
  problem_id: z.string(),
  slug: z.string(),
  version_id: z.string(),
  version_number: z.number().int(),
  title: z.string(),
  statement_md: z.string(),
  difficulty: difficultySchema,
  track_slug: z.string().nullable().optional(),
  mode: problemModeSchema,
  status: problemStatusSchema,
  is_archived: z.boolean().default(false),
  topics: z.array(z.string()),
  skills: z.array(z.string()),
  prerequisites: z.array(z.string()),
  learning_objectives: z.array(z.string()),
  examples: z.array(problemExampleSchema),
  time_limit_ms: z.number().int(),
  memory_limit_kb: z.number().int(),
  variants: z.array(adminVariantDetailSchema),
  test_cases: z.array(adminTestCaseDetailSchema),
  reviews: z.array(adminContentReviewItemSchema),
  assigned_courses_count: z.number().int().default(0),
  validated_at: z.string().nullable().optional(),
  published_at: z.string().nullable().optional(),
});

export const adminProblemVersionSummarySchema = z.object({
  version_id: z.string(),
  version_number: z.number().int(),
  title: z.string(),
  statement_md: z.string(),
  difficulty: difficultySchema,
  track_slug: z.string().nullable().optional(),
  mode: problemModeSchema,
  status: problemStatusSchema,
  topics: z.array(z.string()),
  skills: z.array(z.string()),
  time_limit_ms: z.number().int(),
  memory_limit_kb: z.number().int(),
  test_case_count: z.number().int(),
  hidden_test_count: z.number().int(),
  is_current_published: z.boolean(),
  validated_at: z.string().nullable().optional(),
  published_at: z.string().nullable().optional(),
  created_at: z.string(),
  reviews: z.array(adminContentReviewItemSchema).default([]),
});

export const adminProblemVersionsResponseSchema = z.object({
  problem_id: z.string(),
  slug: z.string(),
  current_published_version_id: z.string().nullable().optional(),
  versions: z.array(adminProblemVersionSummarySchema),
});

export const adminProblemArchiveResponseSchema = z.object({
  problem_id: z.string(),
  slug: z.string(),
  is_archived: z.boolean(),
  latest_version_status: problemStatusSchema,
  assigned_courses_count: z.number().int(),
  message: z.string(),
});

export const adminValidationReportSchema = z.object({
  problem_id: z.string(),
  version_id: z.string(),
  passed: z.boolean(),
  new_status: problemStatusSchema,
  quality_warnings: z.array(z.string()).default([]),
  variant_results: z.array(
    z.object({
      language_slug: z.string(),
      syntax_ok: z.boolean().default(true),
      syntax_errors: z.array(z.string()).default([]),
      reference_passed: z.number().int(),
      total_tests: z.number().int(),
      reference_all_passed: z.boolean(),
      buggy_starter_tested: z.boolean(),
      buggy_starter_failed_as_expected: z.boolean().nullable().optional(),
      observed_buggy_failure_category: z.string().nullable().optional(),
      max_runtime_ms: z.number().int().nullable().optional(),
      max_memory_kb: z.number().int().nullable().optional(),
      errors: z.array(z.string()),
    }),
  ),
});

export type Difficulty = z.infer<typeof difficultySchema>;
export type ProblemMode = z.infer<typeof problemModeSchema>;
export type ProblemStatus = z.infer<typeof problemStatusSchema>;
export type Verdict = z.infer<typeof verdictSchema>;
export type StudentProblemListItem = z.infer<typeof studentProblemListItemSchema>;
export type StudentProblemDetail = z.infer<typeof studentProblemDetailSchema>;
export type SubmissionResponse = z.infer<typeof submissionResponseSchema>;
export type SubmissionSummaryItem = z.infer<typeof submissionSummaryItemSchema>;
export type ExecutionAvailability = z.infer<typeof executionAvailabilitySchema>;
export type RevisionResponse = z.infer<typeof revisionResponseSchema>;
export type AdminProblemListItem = z.infer<typeof adminProblemListItemSchema>;
export type AdminProblemDetail = z.infer<typeof adminProblemDetailSchema>;
export type AdminProblemVersionsResponse = z.infer<
  typeof adminProblemVersionsResponseSchema
>;
export type AdminProblemArchiveResponse = z.infer<
  typeof adminProblemArchiveResponseSchema
>;
export type AdminValidationReport = z.infer<typeof adminValidationReportSchema>;
