"""Pydantic schemas for Phase 6: Learning DNA, Adaptive Daily Plans, History & Retention."""

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DnaDimensionKey = Literal["tracing", "coding", "debugging", "testing", "transfer", "retention"]
DnaEvidenceBand = Literal["unobserved", "emerging", "developing", "verified"]
DailyTaskType = Literal["diagnostic", "lesson", "problem", "debugging", "transfer", "retention"]
DailyTaskStatus = Literal["pending", "completed", "skipped"]
HistoryCategory = Literal[
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
]
RetentionScheduleStatus = Literal["scheduled", "due", "passed_retained", "needs_review"]
RetentionOutcome = Literal["retained_verified", "passed_too_early", "needs_review"]


# ---------------------------------------------------------------------------
# A. Learning DNA
# ---------------------------------------------------------------------------


class LearningDnaDimensionView(BaseModel):
    dimension: DnaDimensionKey
    label_en: str
    label_bn: str
    evidence_band: DnaEvidenceBand
    evidence_count: int = Field(..., ge=0)
    factual_metrics: dict[str, int | float | str]
    summary_en: str
    summary_bn: str
    uncertainty_note: str


class LearningDnaSnapshotSummaryView(BaseModel):
    id: UUID
    selected_track_slug: str
    computed_at: datetime
    strengths: list[str]
    growth_areas: list[str]


class LearningDnaProfileView(BaseModel):
    snapshot_id: UUID
    language_slug: str = "python"
    computed_at: datetime
    selected_track_slug: str
    dimensions: list[LearningDnaDimensionView]
    skill_state_summary: dict[str, int]
    strengths: list[str]
    growth_areas: list[str]
    source_counts: dict[str, int]
    methodology_note_en: str
    methodology_note_bn: str
    recent_snapshots: list[LearningDnaSnapshotSummaryView] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# B. Adaptive Daily Learning Plan
# ---------------------------------------------------------------------------


class DailyPlanTaskView(BaseModel):
    id: UUID
    task_order: int
    task_type: DailyTaskType
    skill_slug: str | None = None
    target_id: str
    target_slug: str
    title_en: str
    title_bn: str
    reason_en: str
    reason_bn: str
    href: str
    estimated_minutes: int
    status: DailyTaskStatus
    completed_at: datetime | None = None
    completion_evidence_ref: str | None = None


class DailyLearningPlanView(BaseModel):
    id: UUID
    language_slug: str = "python"
    plan_date: date
    version_number: int
    is_active: bool
    selected_track_slug: str
    available_minutes: int
    total_estimated_minutes: int
    completed_tasks: int
    total_tasks: int
    generation_reason_en: str
    generation_reason_bn: str
    tasks: list[DailyPlanTaskView]
    created_at: datetime
    updated_at: datetime


class DailyPlanHistoryItemView(BaseModel):
    id: UUID
    plan_date: date
    version_number: int
    is_active: bool
    available_minutes: int
    total_estimated_minutes: int
    completed_tasks: int
    total_tasks: int
    created_at: datetime


class DailyPlanWorkspaceView(BaseModel):
    active_plan: DailyLearningPlanView
    history: list[DailyPlanHistoryItemView] = Field(default_factory=list)


class RegenerateDailyPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available_minutes: int | None = Field(default=None, ge=15, le=240)


class UpdateDailyTaskStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: DailyTaskStatus
    completion_evidence_ref: str | None = Field(default=None, max_length=120)


# ---------------------------------------------------------------------------
# C. Persistent Learning History
# ---------------------------------------------------------------------------


class LearningHistoryItemView(BaseModel):
    id: str
    category: HistoryCategory
    title_en: str
    title_bn: str
    summary_en: str
    summary_bn: str
    verdict_or_status: str | None = None
    skill_slug: str | None = None
    href: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime


class LearningHistoryResponseView(BaseModel):
    items: list[LearningHistoryItemView]
    total: int
    limit: int
    offset: int
    category_counts: dict[str, int]


# ---------------------------------------------------------------------------
# D. Retention Verification
# ---------------------------------------------------------------------------


class RetentionScheduleView(BaseModel):
    id: UUID
    language_slug: str = "python"
    skill_slug: str
    skill_title_en: str
    skill_title_bn: str
    problem_id: UUID
    problem_slug: str
    problem_title: str
    starter_code: str
    source_evidence_type: str
    source_verified_at: datetime
    due_at: datetime
    interval_hours: int
    status: RetentionScheduleStatus
    is_due_now: bool
    hours_until_eligible: float
    last_attempt_at: datetime | None = None
    created_at: datetime


class RetentionAttemptView(BaseModel):
    id: UUID
    schedule_id: UUID
    skill_slug: str
    problem_id: UUID
    submission_id: UUID | None = None
    language_slug: str
    verdict: str
    passed_tests: int
    total_tests: int
    elapsed_hours_since_initial: float
    outcome: RetentionOutcome
    summary_message: str
    created_at: datetime


class RetentionOverviewView(BaseModel):
    schedules: list[RetentionScheduleView]
    recent_attempts: list[RetentionAttemptView]
    due_count: int
    retained_skills_count: int
    policy_note_en: str
    policy_note_bn: str


class SubmitRetentionAttemptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language_slug: str = Field(default="python", min_length=1, max_length=32)
    source_code: str = Field(..., min_length=1, max_length=65536)
    student_explanation: str = Field(..., min_length=10, max_length=3000)


# ---------------------------------------------------------------------------
# E. AI Debugging Timeline (Feature 1 — Persisted Per-Problem Chronology)
# ---------------------------------------------------------------------------

DebuggingStepKind = Literal[
    "problem_started",
    "initial_attempt",
    "error_diagnosed",
    "ai_hint",
    "student_correction",
    "successful_execution",
    "learning_outcome",
]


class DebuggingTimelineStepView(BaseModel):
    """Single factual chronological step inside a student's debugging journey."""

    id: str
    step_kind: DebuggingStepKind
    title: str
    detail: str
    code_excerpt: str | None = None
    verdict_or_status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime


class DebuggingJourneyView(BaseModel):
    """Grouped chronological debugging story for one coding problem from real DB records."""

    problem_id: UUID
    problem_slug: str
    problem_title: str
    language_slug: str
    href: str
    outcome_status: Literal["verified_transfer", "solved", "in_progress"]
    attempts_count: int
    hints_used: int
    diagnoses_count: int
    started_at: datetime
    latest_event_at: datetime
    steps: list[DebuggingTimelineStepView]


class DebuggingTimelineResponseView(BaseModel):
    """Paginated AI Debugging Timeline response built strictly from persisted events."""

    journeys: list[DebuggingJourneyView]
    total_journeys: int
    solved_journeys: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# F. Verified Learning Progress (Feature 2 — Verified vs Estimated Evidence)
# ---------------------------------------------------------------------------


class VerifiedLanguageBreakdownView(BaseModel):
    language_slug: str
    problems_attempted: int
    problems_solved_verified: int
    lessons_completed: int
    total_submissions: int


class DailyActivityPointView(BaseModel):
    day: date
    submissions_count: int
    accepted_count: int
    lessons_completed: int


class VerifiedLearningProgressView(BaseModel):
    """Strict separation of execution-verified achievements vs estimated indicators."""

    # Execution & Assessment-Verified Achievements
    problems_attempted: int
    problems_solved_verified: int
    total_submissions: int
    accepted_submissions: int
    languages_used: list[VerifiedLanguageBreakdownView]
    concepts_mastered_verified: list[str]
    concepts_in_progress: list[str]
    assignments_completed_verified: int
    assignments_total: int
    average_published_grade_pct: float | None = None
    transfer_verifications_passed: int
    retention_checks_passed: int
    consistency_active_days_14d: int
    daily_activity_14d: list[DailyActivityPointView]
    improvement_trend: Literal["improving", "steady", "needs_focus", "insufficient_data"]
    early_acceptance_rate_pct: float | None = None
    recent_acceptance_rate_pct: float | None = None

    # Clearly Labeled Estimated / In-Progress Indicators
    estimated_lessons_completed: int
    estimated_diagnostic_sessions: int
    estimated_guided_skills_count: int
    methodology_note: str
