from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MentorState = Literal[
    "awaiting_submission",
    "diagnosing",
    "asking_question",
    "awaiting_student_response",
    "giving_hint",
    "awaiting_revision",
    "verifying",
    "completed",
    "fallback",
]
ProviderMode = Literal["live_llm", "deterministic_fallback"]
KnowledgeStatus = Literal["draft", "approved", "archived"]
VerificationOutcome = Literal["in_progress", "verified_independent", "attempted_not_verified"]


class MLCandidateScore(BaseModel):
    error_code: str
    display_name: str
    probability: float = Field(..., ge=0.0, le=1.0)


class MLDiagnosisResponse(BaseModel):
    id: UUID | None = None
    submission_id: UUID | None = None
    model_version: str
    predicted_error_code: str
    predicted_display_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    is_low_confidence: bool
    uncertainty_note: str
    top_candidates: list[MLCandidateScore]


class RagCitation(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_slug: str
    source_title: str
    source_name: str
    source_version: str
    topic: str
    heading: str
    excerpt: str
    similarity: float = Field(..., ge=-1.0, le=1.0)


class MentorStructuredReply(BaseModel):
    """Strict Pydantic schema enforced on every Socratic tutor output."""

    next_state: MentorState
    guiding_question: str = Field(..., min_length=5, max_length=1200)
    hint_text: str | None = Field(default=None, max_length=1200)
    hint_level: int | None = Field(default=None, ge=1, le=3)
    concept_focus: str = Field(..., min_length=2, max_length=120)
    encouragement: str = Field(default="", max_length=400)
    safety_blocked: bool = False


class MentorTurnView(BaseModel):
    id: UUID
    turn_index: int
    role: Literal["student", "mentor", "system"]
    state_after: MentorState
    message_text: str
    structured_payload: dict[str, Any]
    citations: list[RagCitation] = Field(default_factory=list)
    provider_mode: ProviderMode
    created_at: datetime


class MentorSessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    problem_id: UUID
    submission_id: UUID | None = None
    explanation_language: Literal["en", "bn"] | None = None


class MentorTurnCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["diagnose", "respond", "request_hint"] = "respond"
    submission_id: UUID | None = None
    student_message: str = Field(default="", max_length=2000)
    requested_hint_level: int | None = Field(default=None, ge=1, le=3)
    explanation_language: Literal["en", "bn"] | None = None


class MentorSessionDetail(BaseModel):
    id: UUID
    problem_id: UUID
    problem_version_id: UUID
    latest_submission_id: UUID | None = None
    current_state: MentorState
    explanation_language: Literal["en", "bn"]
    learner_level: str
    hints_used: int = Field(..., ge=0, le=3)
    max_hints: int = 3
    provider_mode: ProviderMode
    latest_diagnosis: MLDiagnosisResponse | None = None
    latest_citations: list[RagCitation] = Field(default_factory=list)
    turns: list[MentorTurnView] = Field(default_factory=list)
    transfer_unlocked: bool = False
    verification_link_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(..., pattern=r"^[a-z0-9-]{3,80}$")
    title: str = Field(..., min_length=3, max_length=180)
    language_slug: str = Field(default="python", min_length=1, max_length=32)
    topic: str = Field(..., min_length=2, max_length=64)
    error_codes: list[str] = Field(default_factory=list)
    source_name: str = Field(..., min_length=2, max_length=120)
    source_version: str = Field(default="1.0", min_length=1, max_length=32)
    content_md: str = Field(..., min_length=20)
    status: KnowledgeStatus = "draft"


class KnowledgeDocumentResponse(BaseModel):
    id: UUID
    slug: str
    title: str
    language_slug: str
    topic: str
    error_codes: list[str]
    source_name: str
    source_version: str
    status: KnowledgeStatus
    chunk_count: int
    approved_at: datetime | None = None
    updated_at: datetime


class RagSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=2, max_length=500)
    topic: str | None = None
    error_code: str | None = None
    top_k: int = Field(default=3, ge=1, le=10)


class RagSearchResponse(BaseModel):
    query: str
    matched: bool
    fallback_note: str | None = None
    citations: list[RagCitation]


class TransferChallengeSummary(BaseModel):
    verification_link_id: UUID
    source_problem_id: UUID
    transfer_problem_id: UUID
    transfer_problem_title: str
    transfer_problem_slug: str
    skill_focus: str
    max_hints_allowed: int
    instructions_md: str
    unlocked: bool
    unlock_reason: str
    latest_attempt: "VerificationAttemptView | None" = None


class VerificationAttemptSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_submission_id: UUID | None = None
    language_slug: str = Field(default="python", min_length=1, max_length=32)
    source_code: str = Field(..., min_length=1)
    student_explanation: str = Field(..., min_length=10, max_length=3000)


class VerificationAttemptView(BaseModel):
    id: UUID
    verification_link_id: UUID
    transfer_problem_id: UUID
    transfer_submission_id: UUID | None = None
    hints_used: int
    student_explanation: str
    outcome: VerificationOutcome
    verdict: str
    passed_tests: int
    total_tests: int
    summary_message: str
    created_at: datetime


class LearningEventView(BaseModel):
    id: UUID
    problem_id: UUID | None = None
    submission_id: UUID | None = None
    diagnosis_id: UUID | None = None
    event_type: str
    hints_used: int
    verdict: str | None = None
    verification_outcome: str | None = None
    metadata: dict[str, Any]
    created_at: datetime
