"""Strict Pydantic v2 schemas for Phase 5 Learning Tracks, Lessons, Diagnostics & Skill Graph."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TrackSlug = Literal["absolute_beginner", "basic_university", "intermediate", "advanced"]
SkillState = Literal[
    "unobserved",
    "introduced",
    "guided",
    "independent",
    "transferred",
    "retained",
]
DiagnosticDomain = Literal[
    "variables",
    "syntax_runtime_debugging",
    "conditions",
    "loop_boundaries",
    "arrays_lists",
    "indexing",
    "functions",
    "mixed_logic",
]
DiagnosticDifficulty = Literal["foundation", "core", "stretch"]
DiagnosticQuestionType = Literal["mcq", "code_execution"]
LessonProgressStatus = Literal["not_started", "in_progress", "completed"]


# --- Learning Tracks ---


class LearningTrackView(BaseModel):
    slug: TrackSlug
    title_en: str
    title_bn: str
    summary_en: str
    summary_bn: str
    target_audience_en: str
    target_audience_bn: str
    display_order: int
    recommended_focus_skills: list[str]


class StudentTrackStatus(BaseModel):
    selected_track_slug: TrackSlug
    recommended_track_slug: TrackSlug | None = None
    recommendation_source: Literal[
        "onboarding_initial",
        "diagnostic_evidence",
        "manual_selection",
    ]
    recommendation_reason: str
    diagnostic_completed: bool
    tracks: list[LearningTrackView]


class SelectTrackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    track_slug: TrackSlug


# --- Beginner Learning Lessons ---


class LessonInteractiveExample(BaseModel):
    title: str
    code: str
    input_data: str = ""
    expected_output: str
    explanation_en: str
    explanation_bn: str


class LessonExerciseTestCase(BaseModel):
    name: str
    input_data: str
    expected_output: str


class LessonGuidedExercise(BaseModel):
    prompt_en: str
    prompt_bn: str
    language_slug: str = "python"
    starter_code: str
    test_cases: list[LessonExerciseTestCase] = Field(default_factory=list)


class LessonSummaryView(BaseModel):
    lesson_id: UUID
    version_id: UUID
    slug: str
    skill_slug: str
    display_order: int
    title_en: str
    title_bn: str
    summary_en: str
    summary_bn: str
    prerequisite_lesson_slugs: list[str]
    track_slugs: list[str]
    estimated_minutes: int
    progress_status: LessonProgressStatus
    reading_completed: bool
    exercise_passed: bool
    exercise_attempts: int
    prerequisites_met: bool


class LessonDetailView(LessonSummaryView):
    content_en_md: str
    content_bn_md: str
    learning_objectives: list[str]
    interactive_examples: list[LessonInteractiveExample]
    guided_exercise: LessonGuidedExercise
    last_code: str | None = None
    last_verdict: str | None = None
    last_stdout: str | None = None
    last_stderr: str | None = None
    completed_at: datetime | None = None


class LessonReadingCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reading_completed: bool = True


class LessonExerciseRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_code: str = Field(..., min_length=1, max_length=20000)


class LessonExerciseCaseResult(BaseModel):
    name: str
    input_data: str
    expected_output: str
    actual_output: str | None = None
    stderr: str | None = None
    compile_output: str | None = None
    verdict: str
    passed: bool


class LessonExerciseRunResponse(BaseModel):
    lesson_id: UUID
    verdict: str
    passed_tests: int
    total_tests: int
    exercise_passed: bool
    progress_status: LessonProgressStatus
    skill_state_after: SkillState
    case_results: list[LessonExerciseCaseResult]


# --- Adaptive Diagnostic Assessment ---


class DiagnosticOptionView(BaseModel):
    id: str
    text_en: str
    text_bn: str


class DiagnosticQuestionPublicView(BaseModel):
    """Public student-facing diagnostic item — NEVER contains correct_option_id or hidden tests."""

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
    language_slug: str = "python"


class DiagnosticSessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explanation_language: Literal["en", "bn"] = "en"


class DiagnosticAnswerSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: UUID
    selected_option_id: str | None = Field(default=None, max_length=32)
    source_code: str | None = Field(default=None, max_length=20000)
    response_time_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class DiagnosticDomainEvidence(BaseModel):
    domain_slug: DiagnosticDomain
    observed_attempts: int
    observed_correct: int
    execution_verified: bool
    evidence_status: Literal[
        "insufficient_evidence",
        "gap_detected",
        "guided_needed",
        "demonstrated_basic",
        "demonstrated_strong",
    ]
    note_en: str
    note_bn: str


class DiagnosticResponseFeedback(BaseModel):
    question_id: UUID
    domain_slug: DiagnosticDomain
    difficulty: DiagnosticDifficulty
    question_type: DiagnosticQuestionType
    is_correct: bool
    execution_verdict: str | None = None
    passed_tests: int = 0
    total_tests: int = 0
    execution_stderr: str | None = None
    feedback_en: str
    feedback_bn: str
    adaptive_action: str | None = None


class DiagnosticSessionView(BaseModel):
    id: UUID
    status: Literal["in_progress", "completed", "abandoned"]
    explanation_language: Literal["en", "bn"]
    answered_count: int
    remaining_count: int
    adaptive_followups_added: int
    current_question: DiagnosticQuestionPublicView | None = None
    last_feedback: DiagnosticResponseFeedback | None = None
    recommended_track_slug: TrackSlug | None = None
    recommendation_rationale: str | None = None
    domain_evidence: list[DiagnosticDomainEvidence] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime | None = None


# --- Prerequisite-Aware Skill Graph ---


class SkillNodeStateView(BaseModel):
    slug: str
    title_en: str
    title_bn: str
    description_en: str
    description_bn: str
    domain_slug: str
    tier: int
    display_order: int
    prerequisites: list[str]
    state: SkillState
    evidence_count: int
    uncertainty_note: str
    last_evidence_type: str | None = None
    last_evidence_at: datetime | None = None


class SkillTransitionView(BaseModel):
    id: UUID
    skill_slug: str
    from_state: str
    to_state: str
    evidence_source: str
    reason: str
    created_at: datetime


class SkillGraphView(BaseModel):
    nodes: list[SkillNodeStateView]
    recent_transitions: list[SkillTransitionView]
    state_legend: list[dict[str, str]]


# --- Explainable Adaptive Recommendations & Dashboard ---


class RecommendationItemView(BaseModel):
    recommendation_type: Literal[
        "diagnostic_assessment",
        "lesson",
        "problem",
        "transfer_challenge",
    ]
    target_id: str
    target_slug: str
    title: str
    priority: int
    reason_en: str
    reason_bn: str
    evidence_factors: list[str]
    href: str


class LearningDashboardView(BaseModel):
    track_status: StudentTrackStatus
    lessons_completed: int
    lessons_total: int
    diagnostic_sessions_completed: int
    latest_diagnostic: DiagnosticSessionView | None = None
    skill_graph: SkillGraphView
    recommendations: list[RecommendationItemView]


# --- Admin Content Governance Schemas (Phase 5) ---


class AdminLessonCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(..., pattern=r"^[a-z0-9-]{3,80}$")
    skill_slug: str = Field(..., min_length=3, max_length=64)
    display_order: int = Field(..., ge=1, le=500)
    title_en: str = Field(..., min_length=3, max_length=180)
    title_bn: str = Field(..., min_length=2, max_length=180)
    summary_en: str = Field(..., min_length=10, max_length=400)
    summary_bn: str = Field(..., min_length=5, max_length=400)
    content_en_md: str = Field(..., min_length=20)
    content_bn_md: str = Field(..., min_length=20)
    learning_objectives: list[str] = Field(default_factory=list)
    prerequisite_lesson_slugs: list[str] = Field(default_factory=list)
    track_slugs: list[TrackSlug] = Field(default_factory=list)
    interactive_examples: list[LessonInteractiveExample] = Field(default_factory=list)
    guided_exercise: LessonGuidedExercise
    estimated_minutes: int = Field(default=15, ge=5, le=120)
    publish: bool = False


class AdminDiagnosticQuestionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(..., pattern=r"^[a-z0-9-]{3,80}$")
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
    publish: bool = False
