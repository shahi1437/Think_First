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
