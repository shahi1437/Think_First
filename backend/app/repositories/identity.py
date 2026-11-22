from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.identity import AuditLog, Profile, UserPreference, UserRole
from app.schemas.identity import (
    ExplanationLanguage,
    LearningGoal,
    PreferredLanguage,
    ProgrammingExperience,
    RecommendedEntryTrack,
    RoleName,
    StartingPreference,
)


@dataclass(slots=True)
class PreferencesRecord:
    user_id: UUID
    programming_experience: ProgrammingExperience
    preferred_language: PreferredLanguage
    learning_goal: LearningGoal
    daily_practice_minutes: int
    preferred_explanation_language: ExplanationLanguage
    starting_preference: StartingPreference
    recommended_entry_track: RecommendedEntryTrack
    active_language_slug: PreferredLanguage = "python"


@dataclass(slots=True)
class UserRecord:
    id: UUID
    email: str
    full_name: str
    avatar_url: str | None
    roles: list[RoleName]
    onboarding_completed: bool
    onboarding_completed_at: datetime | None
    created_at: datetime
    preferences: PreferencesRecord | None = None


@dataclass(slots=True)
class AuditRecord:
    actor_user_id: UUID | None
    action: str
    target_type: str
    target_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None


class IdentityRepository(Protocol):
    """Persistence contract for profiles, preferences, roles, and audit logs."""

    async def get_user_by_id(self, user_id: UUID) -> UserRecord | None: ...

    async def ensure_student_profile(
        self, user_id: UUID, email: str, full_name: str = ""
    ) -> UserRecord: ...

    async def upsert_preferences(
        self,
        *,
        user_id: UUID,
        programming_experience: ProgrammingExperience,
        preferred_language: PreferredLanguage,
        learning_goal: LearningGoal,
        daily_practice_minutes: int,
        preferred_explanation_language: ExplanationLanguage,
        starting_preference: StartingPreference,
        recommended_entry_track: RecommendedEntryTrack,
        active_language_slug: PreferredLanguage | None = None,
        full_name: str | None = None,
        mark_onboarding_completed: bool = False,
    ) -> UserRecord: ...

    async def set_active_language(
        self,
        *,
        user_id: UUID,
        language_slug: PreferredLanguage,
    ) -> UserRecord: ...

    async def list_users(
        self,
        *,
        limit: int,
        offset: int,
        role: RoleName | None = None,
        q: str | None = None,
    ) -> tuple[list[UserRecord], int]: ...

    async def grant_role(
        self, *, user_id: UUID, role: RoleName, granted_by: UUID
    ) -> list[RoleName]: ...

    async def revoke_role(self, *, user_id: UUID, role: RoleName) -> list[RoleName]: ...

    async def count_users_with_role(self, role: RoleName) -> int: ...

    async def record_audit_log(self, event: AuditRecord) -> None: ...


def _to_user_record(profile: Profile) -> UserRecord:
    valid_roles: list[RoleName] = sorted(
        {r.role for r in profile.roles if r.role in ("student", "teacher", "admin")}  # type: ignore[misc]
    )
    pref: PreferencesRecord | None = None
    if profile.preferences is not None:
        p = profile.preferences
        track = p.recommended_entry_track or "diagnostic_assessment"
        pref = PreferencesRecord(
            user_id=p.user_id,
            programming_experience=p.programming_experience,  # type: ignore[arg-type]
            preferred_language=p.preferred_language,  # type: ignore[arg-type]
            active_language_slug=(p.active_language_slug or p.preferred_language or "python"),  # type: ignore[arg-type]
            learning_goal=p.learning_goal,  # type: ignore[arg-type]
            daily_practice_minutes=p.daily_practice_minutes,
            preferred_explanation_language=p.preferred_explanation_language,  # type: ignore[arg-type]
            starting_preference=p.starting_preference,  # type: ignore[arg-type]
            recommended_entry_track=track,  # type: ignore[arg-type]
        )
    return UserRecord(
        id=profile.id,
        email=profile.email,
        full_name=profile.full_name,
        avatar_url=profile.avatar_url,
        roles=valid_roles,
        onboarding_completed=profile.onboarding_completed,
        onboarding_completed_at=profile.onboarding_completed_at,
        created_at=profile.created_at,
        preferences=pref,
    )


class SQLAlchemyIdentityRepository:
    """Async SQLAlchemy implementation backed by Supabase PostgreSQL tables."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _load_profile(self, user_id: UUID) -> Profile | None:
        stmt = (
            select(Profile)
            .where(Profile.id == user_id)
            .options(selectinload(Profile.roles), selectinload(Profile.preferences))
            .execution_options(populate_existing=True)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> UserRecord | None:
        profile = await self._load_profile(user_id)
        return _to_user_record(profile) if profile is not None else None

    async def ensure_student_profile(
        self, user_id: UUID, email: str, full_name: str = ""
    ) -> UserRecord:
        existing = await self._load_profile(user_id)
        if existing is not None:
            return _to_user_record(existing)

        profile = Profile(
            id=user_id,
            email=email.lower(),
            full_name=full_name.strip(),
            onboarding_completed=False,
        )
        self._session.add(profile)
        self._session.add(UserRole(user_id=user_id, role="student", granted_by=None))
        await self._session.commit()

        created = await self._load_profile(user_id)
        if created is None:
            raise RuntimeError("Failed to reload provisioned profile")
        return _to_user_record(created)

    async def upsert_preferences(
        self,
        *,
        user_id: UUID,
        programming_experience: ProgrammingExperience,
        preferred_language: PreferredLanguage,
        learning_goal: LearningGoal,
        daily_practice_minutes: int,
        preferred_explanation_language: ExplanationLanguage,
        starting_preference: StartingPreference,
        recommended_entry_track: RecommendedEntryTrack,
        active_language_slug: PreferredLanguage | None = None,
        full_name: str | None = None,
        mark_onboarding_completed: bool = False,
    ) -> UserRecord:
        profile = await self._load_profile(user_id)
        if profile is None:
            raise KeyError(f"Profile {user_id} not found")

        if full_name is not None:
            profile.full_name = full_name.strip()

        if mark_onboarding_completed and not profile.onboarding_completed:
            profile.onboarding_completed = True
            profile.onboarding_completed_at = datetime.now(UTC)

        effective_active = active_language_slug or preferred_language

        if profile.preferences is None:
            pref = UserPreference(
                user_id=user_id,
                programming_experience=programming_experience,
                preferred_language=preferred_language,
                active_language_slug=effective_active,
                learning_goal=learning_goal,
                daily_practice_minutes=daily_practice_minutes,
                preferred_explanation_language=preferred_explanation_language,
                starting_preference=starting_preference,
                recommended_entry_track=recommended_entry_track,
            )
            profile.preferences = pref
            self._session.add(pref)
        else:
            pref = profile.preferences
            pref.programming_experience = programming_experience
            pref.preferred_language = preferred_language
            if active_language_slug is not None:
                pref.active_language_slug = active_language_slug
            elif mark_onboarding_completed:
                pref.active_language_slug = preferred_language
            pref.learning_goal = learning_goal
            pref.daily_practice_minutes = daily_practice_minutes
            pref.preferred_explanation_language = preferred_explanation_language
            pref.starting_preference = starting_preference
            pref.recommended_entry_track = recommended_entry_track

        await self._session.commit()
        updated = await self._load_profile(user_id)
        if updated is None:
            raise RuntimeError("Failed to reload updated profile")
        return _to_user_record(updated)

    async def set_active_language(
        self,
        *,
        user_id: UUID,
        language_slug: PreferredLanguage,
    ) -> UserRecord:
        profile = await self._load_profile(user_id)
        if profile is None:
            raise KeyError(f"Profile {user_id} not found")
        if profile.preferences is None:
            pref = UserPreference(
                user_id=user_id,
                preferred_language=language_slug,
                active_language_slug=language_slug,
            )
            profile.preferences = pref
            self._session.add(pref)
        else:
            profile.preferences.active_language_slug = language_slug
            profile.preferences.preferred_language = language_slug
        await self._session.commit()
        updated = await self._load_profile(user_id)
        if updated is None:
            raise RuntimeError("Failed to reload updated profile")
        return _to_user_record(updated)

    async def list_users(
        self,
        *,
        limit: int,
        offset: int,
        role: RoleName | None = None,
        q: str | None = None,
    ) -> tuple[list[UserRecord], int]:
        base = select(Profile)
        if role is not None:
            role_user_ids = select(UserRole.user_id).where(UserRole.role == role)
            base = base.where(Profile.id.in_(role_user_ids))
        if q and q.strip():
            term = f"%{q.strip()}%"
            base = base.where(or_(Profile.email.ilike(term), Profile.full_name.ilike(term)))

        total_stmt = select(func.count()).select_from(base.subquery())
        total = int((await self._session.execute(total_stmt)).scalar_one())

        rows_stmt = (
            base.options(selectinload(Profile.roles), selectinload(Profile.preferences))
            .order_by(Profile.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        profiles = list((await self._session.execute(rows_stmt)).scalars().all())
        return [_to_user_record(p) for p in profiles], total

    async def grant_role(
        self, *, user_id: UUID, role: RoleName, granted_by: UUID
    ) -> list[RoleName]:
        profile = await self._load_profile(user_id)
        if profile is None:
            raise KeyError(f"Profile {user_id} not found")

        existing_roles = {r.role for r in profile.roles}
        if role not in existing_roles:
            self._session.add(UserRole(user_id=user_id, role=role, granted_by=granted_by))
            await self._session.commit()

        reloaded = await self._load_profile(user_id)
        return _to_user_record(reloaded).roles if reloaded is not None else []

    async def revoke_role(self, *, user_id: UUID, role: RoleName) -> list[RoleName]:
        profile = await self._load_profile(user_id)
        if profile is None:
            raise KeyError(f"Profile {user_id} not found")

        for item in list(profile.roles):
            if item.role == role:
                await self._session.delete(item)
        await self._session.commit()

        reloaded = await self._load_profile(user_id)
        return _to_user_record(reloaded).roles if reloaded is not None else []

    async def count_users_with_role(self, role: RoleName) -> int:
        stmt = select(func.count()).select_from(UserRole).where(UserRole.role == role)
        return int((await self._session.execute(stmt)).scalar_one())

    async def record_audit_log(self, event: AuditRecord) -> None:
        log = AuditLog(
            actor_user_id=event.actor_user_id,
            action=event.action,
            target_type=event.target_type,
            target_id=event.target_id,
            metadata_json=event.metadata,
            request_id=event.request_id,
        )
        self._session.add(log)
        await self._session.commit()
