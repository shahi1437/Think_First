from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

RoleName = Literal["student", "teacher", "admin"]
ProgrammingExperience = Literal["none", "beginner", "basic", "intermediate", "advanced"]
PreferredLanguage = Literal["python", "javascript", "c", "cpp", "java"]
LearningGoal = Literal[
    "school_fundamentals",
    "university_coursework",
    "debugging_mastery",
    "interview_prep",
    "competitive_programming",
]
ExplanationLanguage = Literal["en", "bn"]
StartingPreference = Literal["guided_beginner", "diagnostic_assessment"]
RecommendedEntryTrack = Literal["foundation_lessons", "diagnostic_assessment"]


class UserPreferencesResponse(BaseModel):
    """Persisted learning preferences and deterministic entry-track recommendation."""

    programming_experience: ProgrammingExperience
    preferred_language: PreferredLanguage
    active_language_slug: PreferredLanguage = "python"
    learning_goal: LearningGoal
    daily_practice_minutes: int = Field(..., ge=10, le=240)
    preferred_explanation_language: ExplanationLanguage
    starting_preference: StartingPreference
    recommended_entry_track: RecommendedEntryTrack
    recommendation_rationale: str
    entry_redirect_path: str = "/student"


class UserPreferencesUpdate(BaseModel):
    """Mutable student learning preferences (extra fields forbidden to prevent role injection)."""

    model_config = ConfigDict(extra="forbid")

    programming_experience: ProgrammingExperience | None = None
    preferred_language: PreferredLanguage | None = None
    active_language_slug: PreferredLanguage | None = None
    learning_goal: LearningGoal | None = None
    daily_practice_minutes: int | None = Field(default=None, ge=10, le=240)
    preferred_explanation_language: ExplanationLanguage | None = None
    starting_preference: StartingPreference | None = None


class OnboardingSubmitRequest(BaseModel):
    """Smart onboarding submission payload (extra fields forbidden)."""

    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    programming_experience: ProgrammingExperience
    preferred_language: PreferredLanguage
    learning_goal: LearningGoal
    daily_practice_minutes: int = Field(..., ge=10, le=240)
    preferred_explanation_language: ExplanationLanguage
    starting_preference: StartingPreference


class UserMeResponse(BaseModel):
    """Authenticated user profile, DB-backed roles, and onboarding preferences."""

    id: UUID
    email: str
    full_name: str
    avatar_url: str | None = None
    roles: list[RoleName]
    onboarding_completed: bool
    onboarding_completed_at: datetime | None = None
    preferences: UserPreferencesResponse | None = None


class AdminRoleMutationRequest(BaseModel):
    """Admin-only role grant payload."""

    model_config = ConfigDict(extra="forbid")

    role: RoleName


class AdminRoleMutationResponse(BaseModel):
    """Result of an audited Admin role mutation."""

    user_id: UUID
    roles: list[RoleName]
    action: Literal["role.granted", "role.revoked"]


class AdminUserSummary(BaseModel):
    """Admin user directory item."""

    id: UUID
    email: str
    full_name: str
    roles: list[RoleName]
    onboarding_completed: bool
    created_at: datetime


class TeacherScopeResponse(BaseModel):
    """Verified teacher identity scope response."""

    user_id: UUID
    email: str
    roles: list[RoleName]
    authorized_scope: Literal["teacher_courses"] = "teacher_courses"


class PortalVerifyRequest(BaseModel):
    """Portal login verification request (extra fields forbidden)."""

    model_config = ConfigDict(extra="forbid")

    portal: RoleName


TeacherInvitationStatus = Literal["pending", "accepted", "revoked", "expired"]
TeacherInvitationDeliveryStatus = Literal["sent", "delivery_blocked"]
TeacherStatusKind = Literal[
    "active_teacher",
    "existing_user_not_teacher",
    "pending_invitation",
    "expired_invitation",
    "revoked_invitation",
    "not_found",
]


class TeacherInvitationView(BaseModel):
    """Admin view of a teacher invitation record (never exposes raw token or token hash)."""

    id: UUID
    email: str
    full_name: str = ""
    status: TeacherInvitationStatus
    delivery_status: TeacherInvitationDeliveryStatus
    delivery_detail: str
    token_preview: str
    invited_by_id: UUID | None = None
    invited_by_email: str | None = None
    accepted_by_user_id: UUID | None = None
    accepted_at: datetime | None = None
    revoked_by_user_id: UUID | None = None
    revoked_at: datetime | None = None
    resend_count: int = 0
    expires_at: datetime
    created_at: datetime
    updated_at: datetime


class TeacherInvitationCreateRequest(BaseModel):
    """Admin request to invite a new Teacher by email (extra fields forbidden)."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., min_length=5, max_length=254)
    full_name: str = Field(default="", max_length=120)
    expires_in_days: int = Field(default=7, ge=1, le=30)


class TeacherInvitationMutationResponse(BaseModel):
    """Result of creating, resending, or revoking a teacher invitation."""

    invitation: TeacherInvitationView
    invitation_token: str | None = None
    accept_path: str | None = None
    action: Literal[
        "teacher.invitation_created",
        "teacher.invitation_resent",
        "teacher.invitation_revoked",
    ]


class TeacherLookupResponse(BaseModel):
    """Unified Admin lookup of an email across existing accounts and teacher invitations."""

    email: str
    status: TeacherStatusKind
    can_grant_directly: bool
    can_invite: bool
    existing_user: AdminUserSummary | None = None
    latest_invitation: TeacherInvitationView | None = None
    message: str


class TeacherManagementOverviewResponse(BaseModel):
    """Unified Teacher Management payload for Admin Dashboard."""

    active_teachers: list[AdminUserSummary]
    active_teachers_total: int
    invitations: list[TeacherInvitationView]
    invitations_total: int = 0
    invitations_limit: int = 50
    invitations_offset: int = 0
    pending_invitations_count: int


class TeacherInvitationInspectResponse(BaseModel):
    """Public/authenticated inspection of a teacher invitation token prior to acceptance."""

    invitation_id: UUID
    email: str
    full_name: str = ""
    status: TeacherInvitationStatus
    expires_at: datetime
    is_valid: bool
    message: str


class TeacherInvitationAcceptRequest(BaseModel):
    """Authenticated request to accept a teacher invitation token (extra fields forbidden)."""

    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., min_length=16, max_length=256)


class TeacherInvitationAcceptResponse(BaseModel):
    """Verified teacher invitation acceptance response."""

    invitation_id: UUID
    user: UserMeResponse
    action: Literal["teacher.invitation_accepted"] = "teacher.invitation_accepted"


class MlDataConsentUpdateRequest(BaseModel):
    """Explicit opt-in / revocation request for anonymized ML debugging dataset collection."""

    model_config = ConfigDict(extra="forbid")

    consent_granted: bool
    policy_version: str = Field(default="v1", min_length=1, max_length=32)


class MlDataConsentResponse(BaseModel):
    """Current opt-in consent state for anonymized student debugging event export."""

    consent_granted: bool = False
    policy_version: str = "v1"
    scope: str = "anonymized_python_debugging_events"
    updated_at: datetime | None = None
