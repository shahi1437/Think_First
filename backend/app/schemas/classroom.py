"""Pydantic schemas for Phase 7 Classrooms, Assignments, Grading & Teacher Analytics."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

EnrollmentPolicy = Literal["open_with_code", "approval_required"]
CourseStatus = Literal["active", "archived"]
MembershipStatus = Literal["pending", "active", "removed", "left"]
GradingPolicy = Literal["manual_review", "judge0_assisted_manual"]
AssignmentStatus = Literal["draft", "published", "archived"]
SubmissionWorkflowStatus = Literal[
    "not_started",
    "in_progress",
    "submitted",
    "revision_requested",
    "resubmitted",
    "graded",
]
GradeStatus = Literal["draft", "published", "revision_requested"]
FeedbackType = Literal["comment", "revision_request", "grade_release"]
StudentAssignmentFilter = Literal[
    "all", "pending", "submitted", "revision_requested", "graded", "overdue"
]


# ---------------------------------------------------------------------------
# Courses, Invitations & Roster
# ---------------------------------------------------------------------------


class CourseCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=2, max_length=32)
    title: str = Field(..., min_length=3, max_length=160)
    description: str = Field(default="", max_length=2000)
    term: str = Field(default="", max_length=64)
    enrollment_policy: EnrollmentPolicy = "open_with_code"
    allow_student_leave: bool = True


class CourseUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, min_length=2, max_length=32)
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    term: str | None = Field(default=None, max_length=64)
    enrollment_policy: EnrollmentPolicy | None = None
    allow_student_leave: bool | None = None


class InvitationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_uses: int | None = Field(default=None, ge=1, le=500)
    expires_in_hours: int | None = Field(default=168, ge=1, le=2160)


class ClassInvitationView(BaseModel):
    id: UUID
    course_id: UUID
    code_preview: str
    max_uses: int | None = None
    uses_count: int
    expires_at: datetime | None = None
    is_active: bool
    created_at: datetime


class JoinClassRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invite_code: str = Field(..., min_length=6, max_length=40)


class MembershipActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["approve", "remove"]


class RosterMemberView(BaseModel):
    membership_id: UUID
    student_id: UUID
    full_name: str
    email: str
    status: MembershipStatus
    joined_at: datetime
    approved_at: datetime | None = None
    submissions_count: int = 0
    accepted_attempts_count: int = 0
    hints_used_total: int = 0


class CourseSummaryView(BaseModel):
    id: UUID
    teacher_id: UUID
    teacher_name: str
    code: str
    title: str
    description: str
    term: str
    enrollment_policy: EnrollmentPolicy
    allow_student_leave: bool
    status: CourseStatus
    active_students_count: int = 0
    pending_students_count: int = 0
    assignments_count: int = 0
    created_at: datetime
    updated_at: datetime


class StudentEnrolledCourseView(BaseModel):
    membership_id: UUID
    course_id: UUID
    code: str
    title: str
    description: str
    term: str
    teacher_name: str
    course_status: CourseStatus
    membership_status: MembershipStatus
    allow_student_leave: bool
    published_assignments_count: int = 0
    joined_at: datetime


class TeacherCourseDetailView(BaseModel):
    course: CourseSummaryView
    invitations: list[ClassInvitationView]
    roster: list[RosterMemberView]
    assignments: list["AssignmentSummaryView"]
    analytics: "ClassAnalyticsView"


# ---------------------------------------------------------------------------
# Assignments & Problem Links
# ---------------------------------------------------------------------------


class AssignmentProblemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_id: UUID
    points: float = Field(default=100.0, ge=0.0, le=1000.0)


class AssignmentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    course_id: UUID
    title: str = Field(..., min_length=3, max_length=200)
    instructions_md: str = Field(default="", max_length=8000)
    opens_at: datetime | None = None
    due_at: datetime | None = None
    max_marks: float = Field(default=100.0, gt=0.0, le=1000.0)
    grading_policy: GradingPolicy = "judge0_assisted_manual"
    max_attempts: int = Field(default=3, ge=1, le=50)
    allow_ai_hints: bool = True
    hint_limit: int = Field(default=2, ge=0, le=3)
    allow_late_submissions: bool = False
    allow_resubmission_on_revision: bool = True
    publish_now: bool = False
    problems: list[AssignmentProblemInput] = Field(..., min_length=1, max_length=10)


class AssignmentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=3, max_length=200)
    instructions_md: str | None = Field(default=None, max_length=8000)
    opens_at: datetime | None = None
    due_at: datetime | None = None
    max_marks: float | None = Field(default=None, gt=0.0, le=1000.0)
    grading_policy: GradingPolicy | None = None
    max_attempts: int | None = Field(default=None, ge=1, le=50)
    allow_ai_hints: bool | None = None
    hint_limit: int | None = Field(default=None, ge=0, le=3)
    allow_late_submissions: bool | None = None
    allow_resubmission_on_revision: bool | None = None
    problems: list[AssignmentProblemInput] | None = Field(default=None, min_length=1, max_length=10)


class AssignmentProblemLinkView(BaseModel):
    link_id: UUID
    problem_id: UUID
    problem_version_id: UUID
    ordinal: int
    points: float
    slug: str
    title: str
    difficulty: str
    mode: str
    version_number: int


class AssignmentSummaryView(BaseModel):
    id: UUID
    course_id: UUID
    course_code: str
    course_title: str
    title: str
    status: AssignmentStatus
    opens_at: datetime | None = None
    due_at: datetime | None = None
    max_marks: float
    max_attempts: int
    allow_ai_hints: bool
    hint_limit: int
    allow_late_submissions: bool
    allow_resubmission_on_revision: bool
    problem_count: int = 0
    enrolled_students_count: int = 0
    submitted_count: int = 0
    graded_count: int = 0
    pending_grading_count: int = 0
    created_at: datetime


# ---------------------------------------------------------------------------
# Submissions, Attempts, Grading, Feedback & Audit
# ---------------------------------------------------------------------------


class AssignmentAttemptView(BaseModel):
    id: UUID
    problem_id: UUID
    problem_version_id: UUID
    execution_submission_id: UUID | None = None
    attempt_number: int
    language_slug: str
    source_code: str
    student_notes: str
    verdict: str
    passed_tests: int
    total_tests: int
    hints_used: int
    is_late: bool
    submitted_at: datetime


class AssignmentGradeView(BaseModel):
    id: UUID
    marks_awarded: float
    max_marks: float
    status: GradeStatus
    graded_by_name: str
    published_at: datetime | None = None
    updated_at: datetime


class TeacherFeedbackView(BaseModel):
    id: UUID
    feedback_type: FeedbackType
    body_md: str
    teacher_name: str
    is_visible_to_student: bool
    created_at: datetime


class GradingAuditEventView(BaseModel):
    id: UUID
    actor_name: str
    action: str
    previous_marks: float | None = None
    new_marks: float | None = None
    previous_status: str | None = None
    new_status: str | None = None
    notes: str
    created_at: datetime


class TeacherSubmissionReviewItem(BaseModel):
    assignment_submission_id: UUID
    student_id: UUID
    student_name: str
    student_email: str
    status: SubmissionWorkflowStatus
    attempts_used: int
    is_late: bool
    submitted_at: datetime | None = None
    resubmitted_at: datetime | None = None
    latest_attempt: AssignmentAttemptView | None = None
    attempts: list[AssignmentAttemptView] = Field(default_factory=list)
    grade: AssignmentGradeView | None = None
    feedback: list[TeacherFeedbackView] = Field(default_factory=list)
    audit_events: list[GradingAuditEventView] = Field(default_factory=list)


class TeacherAssignmentDetailView(BaseModel):
    assignment: AssignmentSummaryView
    instructions_md: str
    grading_policy: GradingPolicy
    problems: list[AssignmentProblemLinkView]
    submissions: list[TeacherSubmissionReviewItem]


class GradeSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    marks_awarded: float = Field(..., ge=0.0, le=1000.0)
    action: Literal["save_draft", "publish", "request_revision"] = "publish"
    feedback_md: str = Field(default="", max_length=6000)


class StudentAssignmentListItemView(BaseModel):
    assignment_id: UUID
    course_id: UUID
    course_code: str
    course_title: str
    title: str
    opens_at: datetime | None = None
    due_at: datetime | None = None
    max_marks: float
    max_attempts: int
    allow_ai_hints: bool
    hint_limit: int
    allow_late_submissions: bool
    allow_resubmission_on_revision: bool
    problem_count: int
    workflow_status: SubmissionWorkflowStatus
    attempts_used: int
    is_overdue: bool
    is_late: bool
    released_marks: float | None = None
    released_grade_status: GradeStatus | None = None
    submitted_at: datetime | None = None


class StudentAssignmentDetailView(BaseModel):
    assignment: StudentAssignmentListItemView
    instructions_md: str
    grading_policy: GradingPolicy
    problems: list[AssignmentProblemLinkView]
    attempts: list[AssignmentAttemptView]
    can_submit: bool
    submit_block_reason: str | None = None
    grade: AssignmentGradeView | None = None
    feedback: list[TeacherFeedbackView] = Field(default_factory=list)


class StudentAssignmentSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_id: UUID
    language_slug: str = Field(default="python", min_length=1, max_length=32)
    source_code: str = Field(..., min_length=1, max_length=65536)
    student_notes: str = Field(default="", max_length=3000)
    hints_used: int = Field(default=0, ge=0, le=3)


class StudentAssignmentAttemptResponse(BaseModel):
    attempt: AssignmentAttemptView
    workflow_status: SubmissionWorkflowStatus
    attempts_used: int
    attempts_remaining: int


# ---------------------------------------------------------------------------
# Evidence-Based Teacher Dashboard & Class Analytics
# ---------------------------------------------------------------------------


class VerdictCountItem(BaseModel):
    verdict: str
    count: int


class MisconceptionCountItem(BaseModel):
    error_code: str
    occurrences: int


class SkillGapItem(BaseModel):
    skill_slug: str
    unobserved_or_guided_count: int
    verified_count: int


class SupportStudentItem(BaseModel):
    student_id: UUID
    full_name: str
    email: str
    course_title: str
    reason: str
    failed_attempts: int
    hints_used: int


class ClassAnalyticsView(BaseModel):
    active_students: int
    total_attempts: int
    accepted_attempts: int
    verdict_breakdown: list[VerdictCountItem]
    common_misconceptions: list[MisconceptionCountItem]
    skill_gaps: list[SkillGapItem]
    total_hints_used: int
    verified_independent_transfers: int
    students_needing_support: list[SupportStudentItem]


class ClassComparisonItem(BaseModel):
    course_id: UUID
    course_code: str
    course_title: str
    active_students: int
    published_assignments: int
    submitted_count: int
    graded_count: int
    pending_grading_count: int
    total_attempts: int
    accepted_attempts: int
    acceptance_rate_pct: float | None = None


class TeacherStudentAssignmentRecord(BaseModel):
    assignment_id: UUID
    title: str
    due_at: datetime | None = None
    workflow_status: SubmissionWorkflowStatus
    attempts_used: int
    latest_verdict: str | None = None
    marks_awarded: float | None = None
    max_marks: float
    grade_status: GradeStatus | None = None
    submitted_at: datetime | None = None


class TeacherStudentPerformanceView(BaseModel):
    course_id: UUID
    course_code: str
    course_title: str
    student_id: UUID
    full_name: str
    email: str
    membership_status: MembershipStatus
    total_assignment_attempts: int
    accepted_assignment_attempts: int
    hints_used_total: int
    verified_transfers_count: int
    verified_skills: list[str]
    developing_skills: list[str]
    common_misconceptions: list[MisconceptionCountItem]
    assignments: list[TeacherStudentAssignmentRecord]


class TeacherDashboardView(BaseModel):
    courses_count: int
    active_courses_count: int
    total_enrolled_students: int
    active_assignments_count: int
    pending_grading_count: int
    graded_submissions_count: int
    courses: list[CourseSummaryView]
    upcoming_deadlines: list[AssignmentSummaryView]
    analytics: ClassAnalyticsView
    class_comparison: list[ClassComparisonItem] = Field(default_factory=list)
    methodology_note: str
