"""Strict Pydantic v2 schemas for Phase 8 Admin Overview, Curriculum & Governance."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.learning import (
    AdminDiagnosticQuestionCreateRequest,
    AdminLessonCreateRequest,
    DiagnosticDifficulty,
    DiagnosticDomain,
    DiagnosticOptionView,
    DiagnosticQuestionType,
    LessonExerciseTestCase,
    LessonGuidedExercise,
    LessonInteractiveExample,
    TrackSlug,
)
from app.schemas.mentor import KnowledgeDocumentCreateRequest
from app.schemas.problems import AdminProblemCreateRequest, Difficulty, ProblemMode


class AdminAuditLogItem(BaseModel):
    id: UUID
    actor_user_id: UUID | None = None
    actor_email: str | None = None
    actor_name: str | None = None
    action: str
    target_type: str
    target_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None
    created_at: datetime


class AdminReviewQueueItem(BaseModel):
    problem_id: UUID
    version_id: UUID
    slug: str
    title: str
    difficulty: Difficulty
    mode: ProblemMode
    status: str
    version_number: int
    updated_at: datetime


class AdminTrackCoverageItem(BaseModel):
    track_slug: TrackSlug
    title_en: str
    title_bn: str
    lesson_count: int
    problem_count: int
    focus_skills: list[str]


class AdminDashboardOverview(BaseModel):
    problems_total: int
    problems_published: int
    problems_draft: int
    problems_validated: int
    problems_in_review: int
    problems_approved: int
    problems_archived: int
    problems_intermediate_or_advanced: int
    lessons_published: int
    lessons_total: int
    diagnostic_published: int
    diagnostic_stretch_count: int
    knowledge_approved: int
    knowledge_total: int
    skill_nodes_count: int
    students_count: int = 0
    teachers_count: int = 0
    admins_count: int = 0
    courses_total: int = 0
    courses_active: int = 0
    enrollments_active: int = 0
    assignments_published: int = 0
    review_queue: list[AdminReviewQueueItem] = Field(default_factory=list)
    track_coverage: list[AdminTrackCoverageItem] = Field(default_factory=list)
    recent_audit_logs: list[AdminAuditLogItem] = Field(default_factory=list)


class AdminLessonDetailView(BaseModel):
    lesson_id: UUID
    version_id: UUID
    version_number: int
    slug: str
    language_slug: str = "python"
    skill_slug: str
    display_order: int
    status: str
    is_published_current: bool
    title_en: str
    title_bn: str
    summary_en: str
    summary_bn: str
    content_en_md: str
    content_bn_md: str
    learning_objectives: list[str]
    prerequisite_lesson_slugs: list[str]
    track_slugs: list[str]
    interactive_examples: list[LessonInteractiveExample]
    guided_exercise: LessonGuidedExercise
    estimated_minutes: int
    published_at: datetime | None = None
    updated_at: datetime


class AdminLessonStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["draft", "published", "archived"]


class AdminLessonExerciseValidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_solution: str = Field(..., min_length=1, max_length=20000)


class AdminCurriculumValidateResponse(BaseModel):
    target_type: str
    target_id: UUID
    passed: bool
    passed_tests: int
    total_tests: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AdminDiagnosticQuestionDetail(BaseModel):
    id: UUID
    slug: str
    domain_slug: DiagnosticDomain
    skill_slug: str
    difficulty: DiagnosticDifficulty
    question_type: DiagnosticQuestionType
    prompt_en: str
    prompt_bn: str
    code_snippet: str | None = None
    options: list[DiagnosticOptionView] = Field(default_factory=list)
    starter_code: str | None = None
    language_slug: str
    status: str
    correct_option_id: str | None = None
    explanation_en: str
    explanation_bn: str
    evaluation_tests: list[LessonExerciseTestCase] = Field(default_factory=list)
    reference_solution: str | None = None
    validation_summary: dict[str, Any] = Field(default_factory=dict)
    published_at: datetime | None = None
    updated_at: datetime


class AdminDiagnosticQuestionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain_slug: DiagnosticDomain
    skill_slug: str = Field(..., min_length=3, max_length=64)
    difficulty: DiagnosticDifficulty
    question_type: DiagnosticQuestionType
    prompt_en: str = Field(..., min_length=10)
    prompt_bn: str = Field(..., min_length=5)
    code_snippet: str | None = None
    options: list[DiagnosticOptionView] = Field(default_factory=list)
    starter_code: str | None = None
    correct_option_id: str | None = None
    explanation_en: str = Field(..., min_length=10)
    explanation_bn: str = Field(..., min_length=5)
    evaluation_tests: list[LessonExerciseTestCase] = Field(default_factory=list)
    reference_solution: str | None = None


class AdminDiagnosticStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["draft", "approved", "published", "archived"]


class AdminDiagnosticValidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_solution: str | None = None


class AdminTrackUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title_en: str = Field(..., min_length=3, max_length=120)
    title_bn: str = Field(..., min_length=2, max_length=120)
    summary_en: str = Field(..., min_length=10, max_length=600)
    summary_bn: str = Field(..., min_length=5, max_length=600)
    recommended_focus_skills: list[str] = Field(default_factory=list)


class AdminImportLessonItem(AdminLessonCreateRequest):
    reference_solution: str | None = None
    validate_with_judge0: bool = True


class AdminImportProblemItem(AdminProblemCreateRequest):
    validate_with_judge0: bool = True
    publish: bool = True


class AdminImportDiagnosticItem(AdminDiagnosticQuestionCreateRequest):
    reference_solution: str | None = None
    validate_with_judge0: bool = True


class AdminCurriculumImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lessons: list[AdminImportLessonItem] = Field(default_factory=list)
    problems: list[AdminImportProblemItem] = Field(default_factory=list)
    diagnostic_questions: list[AdminImportDiagnosticItem] = Field(default_factory=list)
    knowledge_documents: list[KnowledgeDocumentCreateRequest] = Field(default_factory=list)


class AdminCurriculumImportReport(BaseModel):
    lessons_imported: int
    lessons_validated: int
    problems_imported: int
    problems_validated_and_published: int
    diagnostic_questions_imported: int
    knowledge_documents_imported: int
    errors: list[str] = Field(default_factory=list)


class OperationalCheckStatus(BaseModel):
    name: str
    status: Literal["ok", "degraded", "unavailable"]
    latency_ms: float | None = None
    detail: str


class AdminExecutionFailureStats(BaseModel):
    window_days: int = 7
    total_executions: int = 0
    accepted_executions: int = 0
    failed_executions: int = 0
    failure_rate_pct: float | None = None
    verdict_counts: dict[str, int] = Field(default_factory=dict)
    failures_by_language: dict[str, int] = Field(default_factory=dict)


class AdminUserActivityOverview(BaseModel):
    active_learners_24h: int = 0
    active_learners_7d: int = 0
    submissions_24h: int = 0
    diagnoses_24h: int = 0
    notifications_total: int = 0


class AdminOperationsHealthResponse(BaseModel):
    overall_status: Literal["ok", "degraded"]
    environment: str
    rate_limit_enabled: bool
    llm_provider_mode: Literal["live_llm", "deterministic_fallback"]
    llm_provider: str
    llm_model: str
    checks: list[OperationalCheckStatus] = Field(default_factory=list)
    execution_stats: AdminExecutionFailureStats | None = None
    activity_overview: AdminUserActivityOverview | None = None
