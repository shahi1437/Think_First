import { z } from "zod";

export const enrollmentPolicySchema = z.enum([
  "open_with_code",
  "approval_required",
]);
export type EnrollmentPolicy = z.infer<typeof enrollmentPolicySchema>;

export const courseStatusSchema = z.enum(["active", "archived"]);
export type CourseStatus = z.infer<typeof courseStatusSchema>;

export const membershipStatusSchema = z.enum([
  "pending",
  "active",
  "removed",
  "left",
]);
export type MembershipStatus = z.infer<typeof membershipStatusSchema>;

export const gradingPolicySchema = z.enum([
  "manual_review",
  "judge0_assisted_manual",
]);
export type GradingPolicy = z.infer<typeof gradingPolicySchema>;

export const assignmentStatusSchema = z.enum([
  "draft",
  "published",
  "archived",
]);
export type AssignmentStatus = z.infer<typeof assignmentStatusSchema>;

export const submissionWorkflowStatusSchema = z.enum([
  "not_started",
  "in_progress",
  "submitted",
  "revision_requested",
  "resubmitted",
  "graded",
]);
export type SubmissionWorkflowStatus = z.infer<
  typeof submissionWorkflowStatusSchema
>;

export const gradeStatusSchema = z.enum([
  "draft",
  "published",
  "revision_requested",
]);
export type GradeStatus = z.infer<typeof gradeStatusSchema>;

export const feedbackTypeSchema = z.enum([
  "comment",
  "revision_request",
  "grade_release",
]);
export type FeedbackType = z.infer<typeof feedbackTypeSchema>;

export const studentAssignmentFilterSchema = z.enum([
  "all",
  "pending",
  "submitted",
  "revision_requested",
  "graded",
  "overdue",
]);
export type StudentAssignmentFilter = z.infer<
  typeof studentAssignmentFilterSchema
>;

export const classInvitationViewSchema = z.object({
  id: z.string(),
  course_id: z.string(),
  code_preview: z.string(),
  max_uses: z.number().nullable().optional(),
  uses_count: z.number(),
  expires_at: z.string().nullable().optional(),
  is_active: z.boolean(),
  created_at: z.string(),
});
export type ClassInvitationView = z.infer<typeof classInvitationViewSchema>;

export const rosterMemberViewSchema = z.object({
  membership_id: z.string(),
  student_id: z.string(),
  full_name: z.string(),
  email: z.string(),
  status: membershipStatusSchema,
  joined_at: z.string(),
  approved_at: z.string().nullable().optional(),
  submissions_count: z.number(),
  accepted_attempts_count: z.number(),
  hints_used_total: z.number(),
});
export type RosterMemberView = z.infer<typeof rosterMemberViewSchema>;

export const courseSummaryViewSchema = z.object({
  id: z.string(),
  teacher_id: z.string(),
  teacher_name: z.string(),
  code: z.string(),
  title: z.string(),
  description: z.string(),
  term: z.string(),
  enrollment_policy: enrollmentPolicySchema,
  allow_student_leave: z.boolean(),
  status: courseStatusSchema,
  active_students_count: z.number(),
  pending_students_count: z.number(),
  assignments_count: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type CourseSummaryView = z.infer<typeof courseSummaryViewSchema>;

export const studentEnrolledCourseViewSchema = z.object({
  membership_id: z.string(),
  course_id: z.string(),
  code: z.string(),
  title: z.string(),
  description: z.string(),
  term: z.string(),
  teacher_name: z.string(),
  course_status: courseStatusSchema,
  membership_status: membershipStatusSchema,
  allow_student_leave: z.boolean(),
  published_assignments_count: z.number(),
  joined_at: z.string(),
});
export type StudentEnrolledCourseView = z.infer<
  typeof studentEnrolledCourseViewSchema
>;

export const assignmentProblemLinkViewSchema = z.object({
  link_id: z.string(),
  problem_id: z.string(),
  problem_version_id: z.string(),
  ordinal: z.number(),
  points: z.number(),
  slug: z.string(),
  title: z.string(),
  difficulty: z.string(),
  mode: z.string(),
  version_number: z.number(),
});
export type AssignmentProblemLinkView = z.infer<
  typeof assignmentProblemLinkViewSchema
>;

export const assignmentSummaryViewSchema = z.object({
  id: z.string(),
  course_id: z.string(),
  course_code: z.string(),
  course_title: z.string(),
  title: z.string(),
  status: assignmentStatusSchema,
  opens_at: z.string().nullable().optional(),
  due_at: z.string().nullable().optional(),
  max_marks: z.number(),
  max_attempts: z.number(),
  allow_ai_hints: z.boolean(),
  hint_limit: z.number(),
  allow_late_submissions: z.boolean(),
  allow_resubmission_on_revision: z.boolean(),
  problem_count: z.number(),
  enrolled_students_count: z.number(),
  submitted_count: z.number(),
  graded_count: z.number(),
  pending_grading_count: z.number(),
  created_at: z.string(),
});
export type AssignmentSummaryView = z.infer<typeof assignmentSummaryViewSchema>;

export const assignmentAttemptViewSchema = z.object({
  id: z.string(),
  problem_id: z.string(),
  problem_version_id: z.string(),
  execution_submission_id: z.string().nullable().optional(),
  attempt_number: z.number(),
  language_slug: z.string(),
  source_code: z.string(),
  student_notes: z.string(),
  verdict: z.string(),
  passed_tests: z.number(),
  total_tests: z.number(),
  hints_used: z.number(),
  is_late: z.boolean(),
  submitted_at: z.string(),
});
export type AssignmentAttemptView = z.infer<typeof assignmentAttemptViewSchema>;

export const assignmentGradeViewSchema = z.object({
  id: z.string(),
  marks_awarded: z.number(),
  max_marks: z.number(),
  status: gradeStatusSchema,
  graded_by_name: z.string(),
  published_at: z.string().nullable().optional(),
  updated_at: z.string(),
});
export type AssignmentGradeView = z.infer<typeof assignmentGradeViewSchema>;

export const teacherFeedbackViewSchema = z.object({
  id: z.string(),
  feedback_type: feedbackTypeSchema,
  body_md: z.string(),
  teacher_name: z.string(),
  is_visible_to_student: z.boolean(),
  created_at: z.string(),
});
export type TeacherFeedbackView = z.infer<typeof teacherFeedbackViewSchema>;

export const gradingAuditEventViewSchema = z.object({
  id: z.string(),
  actor_name: z.string(),
  action: z.string(),
  previous_marks: z.number().nullable().optional(),
  new_marks: z.number().nullable().optional(),
  previous_status: z.string().nullable().optional(),
  new_status: z.string().nullable().optional(),
  notes: z.string(),
  created_at: z.string(),
});
export type GradingAuditEventView = z.infer<typeof gradingAuditEventViewSchema>;

export const teacherSubmissionReviewItemSchema = z.object({
  assignment_submission_id: z.string(),
  student_id: z.string(),
  student_name: z.string(),
  student_email: z.string(),
  status: submissionWorkflowStatusSchema,
  attempts_used: z.number(),
  is_late: z.boolean(),
  submitted_at: z.string().nullable().optional(),
  resubmitted_at: z.string().nullable().optional(),
  latest_attempt: assignmentAttemptViewSchema.nullable().optional(),
  attempts: z.array(assignmentAttemptViewSchema),
  grade: assignmentGradeViewSchema.nullable().optional(),
  feedback: z.array(teacherFeedbackViewSchema),
  audit_events: z.array(gradingAuditEventViewSchema),
});
export type TeacherSubmissionReviewItem = z.infer<
  typeof teacherSubmissionReviewItemSchema
>;

export const teacherAssignmentDetailViewSchema = z.object({
  assignment: assignmentSummaryViewSchema,
  instructions_md: z.string(),
  grading_policy: gradingPolicySchema,
  problems: z.array(assignmentProblemLinkViewSchema),
  submissions: z.array(teacherSubmissionReviewItemSchema),
});
export type TeacherAssignmentDetailView = z.infer<
  typeof teacherAssignmentDetailViewSchema
>;

export const studentAssignmentListItemViewSchema = z.object({
  assignment_id: z.string(),
  course_id: z.string(),
  course_code: z.string(),
  course_title: z.string(),
  title: z.string(),
  opens_at: z.string().nullable().optional(),
  due_at: z.string().nullable().optional(),
  max_marks: z.number(),
  max_attempts: z.number(),
  allow_ai_hints: z.boolean(),
  hint_limit: z.number(),
  allow_late_submissions: z.boolean(),
  allow_resubmission_on_revision: z.boolean(),
  problem_count: z.number(),
  workflow_status: submissionWorkflowStatusSchema,
  attempts_used: z.number(),
  is_overdue: z.boolean(),
  is_late: z.boolean(),
  released_marks: z.number().nullable().optional(),
  released_grade_status: gradeStatusSchema.nullable().optional(),
  submitted_at: z.string().nullable().optional(),
});
export type StudentAssignmentListItemView = z.infer<
  typeof studentAssignmentListItemViewSchema
>;

export const studentAssignmentDetailViewSchema = z.object({
  assignment: studentAssignmentListItemViewSchema,
  instructions_md: z.string(),
  grading_policy: gradingPolicySchema,
  problems: z.array(assignmentProblemLinkViewSchema),
  attempts: z.array(assignmentAttemptViewSchema),
  can_submit: z.boolean(),
  submit_block_reason: z.string().nullable().optional(),
  grade: assignmentGradeViewSchema.nullable().optional(),
  feedback: z.array(teacherFeedbackViewSchema),
});
export type StudentAssignmentDetailView = z.infer<
  typeof studentAssignmentDetailViewSchema
>;

export const studentAssignmentAttemptResponseSchema = z.object({
  attempt: assignmentAttemptViewSchema,
  workflow_status: submissionWorkflowStatusSchema,
  attempts_used: z.number(),
  attempts_remaining: z.number(),
});
export type StudentAssignmentAttemptResponse = z.infer<
  typeof studentAssignmentAttemptResponseSchema
>;

export const verdictCountItemSchema = z.object({
  verdict: z.string(),
  count: z.number(),
});

export const misconceptionCountItemSchema = z.object({
  error_code: z.string(),
  occurrences: z.number(),
});

export const skillGapItemSchema = z.object({
  skill_slug: z.string(),
  unobserved_or_guided_count: z.number(),
  verified_count: z.number(),
});

export const supportStudentItemSchema = z.object({
  student_id: z.string(),
  full_name: z.string(),
  email: z.string(),
  course_title: z.string(),
  reason: z.string(),
  failed_attempts: z.number(),
  hints_used: z.number(),
});

export const classAnalyticsViewSchema = z.object({
  active_students: z.number(),
  total_attempts: z.number(),
  accepted_attempts: z.number(),
  verdict_breakdown: z.array(verdictCountItemSchema),
  common_misconceptions: z.array(misconceptionCountItemSchema),
  skill_gaps: z.array(skillGapItemSchema),
  total_hints_used: z.number(),
  verified_independent_transfers: z.number(),
  students_needing_support: z.array(supportStudentItemSchema),
});
export type ClassAnalyticsView = z.infer<typeof classAnalyticsViewSchema>;

export const teacherCourseDetailViewSchema = z.object({
  course: courseSummaryViewSchema,
  invitations: z.array(classInvitationViewSchema),
  roster: z.array(rosterMemberViewSchema),
  assignments: z.array(assignmentSummaryViewSchema),
  analytics: classAnalyticsViewSchema,
});
export type TeacherCourseDetailView = z.infer<
  typeof teacherCourseDetailViewSchema
>;

export const classComparisonItemSchema = z.object({
  course_id: z.string(),
  course_code: z.string(),
  course_title: z.string(),
  active_students: z.number(),
  published_assignments: z.number(),
  submitted_count: z.number(),
  graded_count: z.number(),
  pending_grading_count: z.number(),
  total_attempts: z.number(),
  accepted_attempts: z.number(),
  acceptance_rate_pct: z.number().nullable().optional(),
});
export type ClassComparisonItem = z.infer<typeof classComparisonItemSchema>;

export const teacherStudentAssignmentRecordSchema = z.object({
  assignment_id: z.string(),
  title: z.string(),
  due_at: z.string().nullable().optional(),
  workflow_status: submissionWorkflowStatusSchema,
  attempts_used: z.number(),
  latest_verdict: z.string().nullable().optional(),
  marks_awarded: z.number().nullable().optional(),
  max_marks: z.number(),
  grade_status: gradeStatusSchema.nullable().optional(),
  submitted_at: z.string().nullable().optional(),
});

export const teacherStudentPerformanceViewSchema = z.object({
  course_id: z.string(),
  course_code: z.string(),
  course_title: z.string(),
  student_id: z.string(),
  full_name: z.string(),
  email: z.string(),
  membership_status: membershipStatusSchema,
  total_assignment_attempts: z.number(),
  accepted_assignment_attempts: z.number(),
  hints_used_total: z.number(),
  verified_transfers_count: z.number(),
  verified_skills: z.array(z.string()),
  developing_skills: z.array(z.string()),
  common_misconceptions: z.array(misconceptionCountItemSchema),
  assignments: z.array(teacherStudentAssignmentRecordSchema),
});
export type TeacherStudentPerformanceView = z.infer<
  typeof teacherStudentPerformanceViewSchema
>;

export const teacherDashboardViewSchema = z.object({
  courses_count: z.number(),
  active_courses_count: z.number(),
  total_enrolled_students: z.number(),
  active_assignments_count: z.number(),
  pending_grading_count: z.number(),
  graded_submissions_count: z.number(),
  courses: z.array(courseSummaryViewSchema),
  upcoming_deadlines: z.array(assignmentSummaryViewSchema),
  analytics: classAnalyticsViewSchema,
  class_comparison: z.array(classComparisonItemSchema).optional().default([]),
  methodology_note: z.string(),
});
export type TeacherDashboardView = z.infer<typeof teacherDashboardViewSchema>;
