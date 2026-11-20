from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Difficulty = Literal["beginner", "basic", "intermediate", "advanced"]
TrackSlug = Literal["absolute_beginner", "basic_university", "intermediate", "advanced"]
ProblemMode = Literal["coding", "debugging"]
ProblemStatus = Literal["draft", "validated", "in_review", "approved", "published", "archived"]
SubmissionKind = Literal["run", "submit"]
SubmissionStatus = Literal["queued", "running", "completed", "failed"]
Verdict = Literal[
    "pending",
    "accepted",
    "wrong_answer",
    "compilation_error",
    "runtime_error",
    "time_limit_exceeded",
    "memory_limit_exceeded",
    "internal_error",
]
RevisionType = Literal["autosave", "manual", "run", "submit"]


class LanguageItem(BaseModel):
    slug: str
    display_name: str
    judge0_language_id: int
    monaco_language: str
    version_label: str
    is_enabled: bool


class ProblemExample(BaseModel):
    input: str
    output: str
    explanation: str = ""


class PublicTestCaseView(BaseModel):
    """Student-visible public test case (hidden tests never use this view)."""

    id: UUID
    ordinal: int
    name: str
    input_data: str
    expected_output: str


class StudentLanguageVariantView(BaseModel):
    """Student-visible variant (strictly excludes reference_solution & bug summary)."""

    language_slug: str
    display_name: str
    monaco_language: str
    starter_code: str
    buggy_starter_code: str | None = None
    debugging_prompt: str | None = None


class StudentProblemListItem(BaseModel):
    problem_id: UUID
    version_id: UUID
    slug: str
    title: str
    difficulty: Difficulty
    track_slug: TrackSlug | None = None
    mode: ProblemMode
    topics: list[str]
    skills: list[str]
    supported_languages: list[str]
    published_at: datetime | None = None


class StudentProblemDetail(BaseModel):
    problem_id: UUID
    version_id: UUID
    version_number: int
    slug: str
    title: str
    statement_md: str
    difficulty: Difficulty
    track_slug: TrackSlug | None = None
    mode: ProblemMode
    topics: list[str]
    skills: list[str]
    prerequisites: list[str]
    learning_objectives: list[str]
    examples: list[ProblemExample]
    time_limit_ms: int
    memory_limit_kb: int
    variants: list[StudentLanguageVariantView]
    public_test_cases: list[PublicTestCaseView]
    hidden_test_count: int


class SubmissionCreateRequest(BaseModel):
    """Student Run Code or Submit Code request."""

    model_config = ConfigDict(extra="forbid")

    problem_id: UUID
    language_slug: str = Field(..., min_length=1, max_length=32)
    submission_kind: SubmissionKind
    source_code: str = Field(..., min_length=1)
    prediction_text: str | None = Field(default=None, max_length=2000)
    explanation_text: str | None = Field(default=None, max_length=4000)


class TestCaseExecutionView(BaseModel):
    """Sanitized execution outcome per test case (hidden inputs/outputs always stripped)."""

    ordinal: int
    name: str
    is_hidden: bool
    verdict: Verdict
    input_data: str | None = None
    expected_output: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    compile_output: str | None = None
    runtime_ms: int | None = None
    memory_kb: int | None = None


class SubmissionResponse(BaseModel):
    id: UUID
    problem_id: UUID
    problem_version_id: UUID
    language_slug: str
    submission_kind: SubmissionKind
    source_code: str
    prediction_text: str | None = None
    explanation_text: str | None = None
    status: SubmissionStatus
    verdict: Verdict
    passed_tests: int
    total_tests: int
    runtime_ms: int | None = None
    memory_kb: int | None = None
    execution_evidence: dict[str, Any]
    results: list[TestCaseExecutionView]
    created_at: datetime


class SubmissionSummaryItem(BaseModel):
    id: UUID
    problem_id: UUID
    problem_version_id: UUID
    language_slug: str
    submission_kind: SubmissionKind
    status: SubmissionStatus
    verdict: Verdict
    passed_tests: int
    total_tests: int
    runtime_ms: int | None = None
    memory_kb: int | None = None
    created_at: datetime


class RevisionSaveRequest(BaseModel):
    """Workspace autosave / manual revision request."""

    model_config = ConfigDict(extra="forbid")

    problem_version_id: UUID
    language_slug: str = Field(..., min_length=1, max_length=32)
    source_code: str = Field(..., min_length=1)
    prediction_text: str | None = Field(default=None, max_length=2000)
    explanation_text: str | None = Field(default=None, max_length=4000)
    revision_type: Literal["autosave", "manual"] = "autosave"


class RevisionResponse(BaseModel):
    id: UUID
    problem_version_id: UUID
    language_slug: str
    source_code: str
    prediction_text: str | None = None
    explanation_text: str | None = None
    revision_type: RevisionType
    created_at: datetime


# --- Admin Problem Studio Schemas (Admin-only routes) ---


class AdminTestCaseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ordinal: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=120)
    input_data: str = ""
    expected_output: str
    is_hidden: bool = False
    weight: int = Field(default=1, ge=1, le=100)


class AdminVariantInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language_slug: str = Field(..., min_length=1, max_length=32)
    starter_code: str = Field(..., min_length=1)
    buggy_starter_code: str | None = None
    debugging_prompt: str | None = None
    reference_solution: str = Field(..., min_length=1)
    expected_bug_summary: str | None = None
    expected_failure_category: str | None = None


class AdminProblemCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(..., pattern=r"^[a-z0-9-]{3,80}$")
    title: str = Field(..., min_length=3, max_length=160)
    statement_md: str = Field(..., min_length=10)
    difficulty: Difficulty
    track_slug: TrackSlug | None = None
    mode: ProblemMode
    topics: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)
    examples: list[ProblemExample] = Field(default_factory=list)
    time_limit_ms: int = Field(default=2000, ge=500, le=10000)
    memory_limit_kb: int = Field(default=131072, ge=16384, le=524288)
    variants: list[AdminVariantInput] = Field(..., min_length=1)
    test_cases: list[AdminTestCaseInput] = Field(..., min_length=2)


class AdminProblemUpdateRequest(BaseModel):
    """Creates a new draft version or updates an unpublished draft version."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=3, max_length=160)
    statement_md: str = Field(..., min_length=10)
    difficulty: Difficulty
    track_slug: TrackSlug | None = None
    mode: ProblemMode
    topics: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)
    examples: list[ProblemExample] = Field(default_factory=list)
    time_limit_ms: int = Field(default=2000, ge=500, le=10000)
    memory_limit_kb: int = Field(default=131072, ge=16384, le=524288)
    variants: list[AdminVariantInput] = Field(..., min_length=1)
    test_cases: list[AdminTestCaseInput] = Field(..., min_length=2)


class AdminTestCaseDetail(AdminTestCaseInput):
    id: UUID


class AdminVariantDetail(AdminVariantInput):
    id: UUID


class AdminContentReviewItem(BaseModel):
    id: UUID
    action: str
    notes: str
    validation_summary: dict[str, Any]
    created_at: datetime


class AdminProblemListItem(BaseModel):
    problem_id: UUID
    slug: str
    latest_version_id: UUID
    latest_version_number: int
    title: str
    difficulty: Difficulty
    track_slug: TrackSlug | None = None
    mode: ProblemMode
    status: ProblemStatus
    topics: list[str]
    is_published: bool
    is_archived: bool = False
    updated_at: datetime


class AdminProblemDetail(BaseModel):
    problem_id: UUID
    slug: str
    version_id: UUID
    version_number: int
    title: str
    statement_md: str
    difficulty: Difficulty
    track_slug: TrackSlug | None = None
    mode: ProblemMode
    status: ProblemStatus
    is_archived: bool = False
    topics: list[str]
    skills: list[str]
    prerequisites: list[str]
    learning_objectives: list[str]
    examples: list[ProblemExample]
    time_limit_ms: int
    memory_limit_kb: int
    variants: list[AdminVariantDetail]
    test_cases: list[AdminTestCaseDetail]
    reviews: list[AdminContentReviewItem]
    assigned_courses_count: int = 0
    validated_at: datetime | None = None
    published_at: datetime | None = None


class AdminProblemVersionSummary(BaseModel):
    version_id: UUID
    version_number: int
    title: str
    statement_md: str
    difficulty: Difficulty
    track_slug: TrackSlug | None = None
    mode: ProblemMode
    status: ProblemStatus
    topics: list[str]
    skills: list[str]
    time_limit_ms: int
    memory_limit_kb: int
    test_case_count: int
    hidden_test_count: int
    is_current_published: bool
    validated_at: datetime | None = None
    published_at: datetime | None = None
    created_at: datetime
    reviews: list[AdminContentReviewItem] = Field(default_factory=list)


class AdminProblemVersionsResponse(BaseModel):
    problem_id: UUID
    slug: str
    current_published_version_id: UUID | None = None
    versions: list[AdminProblemVersionSummary]


class AdminReviewActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str = Field(default="", max_length=1000)


class AdminProblemRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str = Field(..., min_length=5, max_length=1000)


class AdminProblemArchiveResponse(BaseModel):
    problem_id: UUID
    slug: str
    is_archived: bool
    latest_version_status: ProblemStatus
    assigned_courses_count: int
    message: str


class AdminValidationVariantResult(BaseModel):
    language_slug: str
    syntax_ok: bool = True
    syntax_errors: list[str] = Field(default_factory=list)
    reference_passed: int
    total_tests: int
    reference_all_passed: bool
    buggy_starter_tested: bool
    buggy_starter_failed_as_expected: bool | None = None
    observed_buggy_failure_category: str | None = None
    max_runtime_ms: int | None = None
    max_memory_kb: int | None = None
    errors: list[str] = Field(default_factory=list)


class AdminValidationReport(BaseModel):
    problem_id: UUID
    version_id: UUID
    passed: bool
    new_status: ProblemStatus
    quality_warnings: list[str] = Field(default_factory=list)
    variant_results: list[AdminValidationVariantResult]


class AdminLanguageSyncResponse(BaseModel):
    synced_count: int
    languages: list[LanguageItem]
