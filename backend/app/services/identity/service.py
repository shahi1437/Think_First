from uuid import UUID

from fastapi import status

from app.core.errors import AppError
from app.core.security import AuthenticatedPrincipal
from app.repositories.identity import (
    AuditRecord,
    IdentityRepository,
    PreferencesRecord,
    UserRecord,
)
from app.schemas.common import PaginatedResponse
from app.schemas.identity import (
    AdminRoleMutationResponse,
    AdminUserSummary,
    OnboardingSubmitRequest,
    ProgrammingExperience,
    RecommendedEntryTrack,
    RoleName,
    StartingPreference,
    UserMeResponse,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)


def recommend_entry_track(
    experience: ProgrammingExperience,
    starting_preference: StartingPreference,
) -> tuple[RecommendedEntryTrack, str]:
    """Deterministically recommend an initial starting point without locking proficiency.

    Actual topic-specific competency is only established through lesson/diagnostic evidence.
    """
    if experience == "none" or starting_preference == "guided_beginner":
        return (
            "foundation_lessons",
            "Starting with structured foundation lessons before the diagnostic assessment "
            "ensures core prerequisites are comfortable. Topic competencies will be measured "
            "from actual exercises rather than self-reported experience.",
        )

    return (
        "diagnostic_assessment",
        "Starting with the 8-area diagnostic assessment to gather concrete topic-level "
        "evidence across syntax, debugging, loops, arrays, and functions before personalizing "
        "your practice track.",
    )


def _format_preferences(pref: PreferencesRecord | None) -> UserPreferencesResponse | None:
    if pref is None:
        return None
    track, rationale = recommend_entry_track(pref.programming_experience, pref.starting_preference)
    entry_redirect_path = (
        "/student/diagnostic?mode=full&entry=onboarding"
        if track == "diagnostic_assessment"
        else "/student"
    )
    return UserPreferencesResponse(
        programming_experience=pref.programming_experience,
        preferred_language=pref.preferred_language,
        active_language_slug=pref.active_language_slug,
        learning_goal=pref.learning_goal,
        daily_practice_minutes=pref.daily_practice_minutes,
        preferred_explanation_language=pref.preferred_explanation_language,
        starting_preference=pref.starting_preference,
        recommended_entry_track=track,
        recommendation_rationale=rationale,
        entry_redirect_path=entry_redirect_path,
    )


def _to_user_me_response(record: UserRecord) -> UserMeResponse:
    return UserMeResponse(
        id=record.id,
        email=record.email,
        full_name=record.full_name,
        avatar_url=record.avatar_url,
        roles=record.roles,
        onboarding_completed=record.onboarding_completed,
        onboarding_completed_at=record.onboarding_completed_at,
        preferences=_format_preferences(record.preferences),
    )


class IdentityService:
    """Handles DB-backed identity resolution, smart onboarding, and audited role governance."""

    def __init__(self, repository: IdentityRepository) -> None:
        self._repo = repository

    async def resolve_authenticated_user(self, principal: AuthenticatedPrincipal) -> UserRecord:
        """Load the user's DB-backed profile and roles (auto-provisioning student row if needed)."""
        user = await self._repo.get_user_by_id(principal.user_id)
        if user is not None:
            return user

        if not principal.email:
            raise AppError(
                code="PROFILE_NOT_FOUND",
                message="User profile is not provisioned and token lacks email claim.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        raw_meta = principal.claims.get("user_metadata")
        full_name = ""
        if isinstance(raw_meta, dict) and isinstance(raw_meta.get("full_name"), str):
            full_name = raw_meta["full_name"]

        return await self._repo.ensure_student_profile(
            user_id=principal.user_id,
            email=principal.email,
            full_name=full_name,
        )

    async def get_me(self, user: UserRecord) -> UserMeResponse:
        return _to_user_me_response(user)

    async def verify_login_portal(
        self,
        *,
        user: UserRecord,
        portal: RoleName,
        request_id: str | None,
    ) -> UserMeResponse:
        """Enforce strict portal separation against DB-backed roles and audit denials."""
        authorized = False
        if portal == "admin":
            authorized = "admin" in user.roles
        elif portal == "teacher":
            authorized = "teacher" in user.roles
        elif portal == "student":
            authorized = (
                "student" in user.roles
                and "teacher" not in user.roles
                and "admin" not in user.roles
            )

        if not authorized:
            await self._repo.record_audit_log(
                AuditRecord(
                    actor_user_id=user.id,
                    action="auth.portal_denied",
                    target_type="portal",
                    target_id=portal,
                    metadata={"requested_portal": portal, "actual_roles": user.roles},
                    request_id=request_id,
                )
            )
            portal_label = portal.capitalize()
            raise AppError(
                code="PORTAL_ACCESS_DENIED",
                message=(
                    f"This account does not have {portal_label} portal access. "
                    "Please use your authorized login portal."
                ),
                status_code=status.HTTP_403_FORBIDDEN,
            )

        return _to_user_me_response(user)

    async def complete_onboarding(
        self,
        *,
        user: UserRecord,
        payload: OnboardingSubmitRequest,
    ) -> UserMeResponse:
        track, _ = recommend_entry_track(
            payload.programming_experience, payload.starting_preference
        )
        updated = await self._repo.upsert_preferences(
            user_id=user.id,
            programming_experience=payload.programming_experience,
            preferred_language=payload.preferred_language,
            learning_goal=payload.learning_goal,
            daily_practice_minutes=payload.daily_practice_minutes,
            preferred_explanation_language=payload.preferred_explanation_language,
            starting_preference=payload.starting_preference,
            recommended_entry_track=track,
            full_name=payload.full_name,
            mark_onboarding_completed=True,
        )
        return _to_user_me_response(updated)

    async def update_preferences(
        self,
        *,
        user: UserRecord,
        payload: UserPreferencesUpdate,
    ) -> UserMeResponse:
        current = user.preferences
        experience = (
            payload.programming_experience
            if payload.programming_experience is not None
            else (current.programming_experience if current else "none")
        )
        preferred_language = (
            payload.preferred_language
            if payload.preferred_language is not None
            else (current.preferred_language if current else "python")
        )
        active_language_slug = (
            payload.active_language_slug
            if payload.active_language_slug is not None
            else (
                payload.preferred_language
                if payload.preferred_language is not None
                else (current.active_language_slug if current else preferred_language)
            )
        )
        learning_goal = (
            payload.learning_goal
            if payload.learning_goal is not None
            else (current.learning_goal if current else "university_coursework")
        )
        daily_practice_minutes = (
            payload.daily_practice_minutes
            if payload.daily_practice_minutes is not None
            else (current.daily_practice_minutes if current else 30)
        )
        explanation_language = (
            payload.preferred_explanation_language
            if payload.preferred_explanation_language is not None
            else (current.preferred_explanation_language if current else "en")
        )
        starting_preference = (
            payload.starting_preference
            if payload.starting_preference is not None
            else (current.starting_preference if current else "diagnostic_assessment")
        )

        track, _ = recommend_entry_track(experience, starting_preference)
        updated = await self._repo.upsert_preferences(
            user_id=user.id,
            programming_experience=experience,
            preferred_language=preferred_language,
            active_language_slug=active_language_slug,
            learning_goal=learning_goal,
            daily_practice_minutes=daily_practice_minutes,
            preferred_explanation_language=explanation_language,
            starting_preference=starting_preference,
            recommended_entry_track=track,
            mark_onboarding_completed=False,
        )
        return _to_user_me_response(updated)

    async def list_users(
        self,
        *,
        limit: int = 25,
        offset: int = 0,
        role: RoleName | None = None,
        q: str | None = None,
    ) -> PaginatedResponse[AdminUserSummary]:
        records, total = await self._repo.list_users(limit=limit, offset=offset, role=role, q=q)
        items = [
            AdminUserSummary(
                id=record.id,
                email=record.email,
                full_name=record.full_name,
                roles=record.roles,
                onboarding_completed=record.onboarding_completed,
                created_at=record.created_at,
            )
            for record in records
        ]
        return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)

    async def grant_role(
        self,
        *,
        actor: UserRecord,
        target_user_id: UUID,
        role: RoleName,
        request_id: str | None,
    ) -> AdminRoleMutationResponse:
        target = await self._repo.get_user_by_id(target_user_id)
        if target is None:
            raise AppError(
                code="USER_NOT_FOUND",
                message="Target user does not exist.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        updated_roles = await self._repo.grant_role(
            user_id=target_user_id,
            role=role,
            granted_by=actor.id,
        )
        await self._repo.record_audit_log(
            AuditRecord(
                actor_user_id=actor.id,
                action="role.granted",
                target_type="user",
                target_id=str(target_user_id),
                metadata={"role": role, "resulting_roles": updated_roles},
                request_id=request_id,
            )
        )
        return AdminRoleMutationResponse(
            user_id=target_user_id,
            roles=updated_roles,
            action="role.granted",
        )

    async def revoke_role(
        self,
        *,
        actor: UserRecord,
        target_user_id: UUID,
        role: RoleName,
        request_id: str | None,
    ) -> AdminRoleMutationResponse:
        target = await self._repo.get_user_by_id(target_user_id)
        if target is None:
            raise AppError(
                code="USER_NOT_FOUND",
                message="Target user does not exist.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if role == "admin" and "admin" in target.roles:
            admin_count = await self._repo.count_users_with_role("admin")
            if admin_count <= 1:
                raise AppError(
                    code="LAST_ADMIN_PROTECTED",
                    message="Cannot revoke admin role from the last remaining administrator.",
                    status_code=status.HTTP_409_CONFLICT,
                )

        if len(target.roles) <= 1 and role in target.roles:
            raise AppError(
                code="LAST_ROLE_PROTECTED",
                message="A user must retain at least one assigned role.",
                status_code=status.HTTP_409_CONFLICT,
            )

        updated_roles = await self._repo.revoke_role(user_id=target_user_id, role=role)
        await self._repo.record_audit_log(
            AuditRecord(
                actor_user_id=actor.id,
                action="role.revoked",
                target_type="user",
                target_id=str(target_user_id),
                metadata={"role": role, "resulting_roles": updated_roles},
                request_id=request_id,
            )
        )
        return AdminRoleMutationResponse(
            user_id=target_user_id,
            roles=updated_roles,
            action="role.revoked",
        )
