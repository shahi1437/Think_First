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
