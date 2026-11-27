import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

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
    TeacherInvitationAcceptResponse,
    TeacherInvitationCreateRequest,
    TeacherInvitationDeliveryStatus,
    TeacherInvitationInspectResponse,
    TeacherInvitationMutationResponse,
    TeacherInvitationStatus,
    TeacherInvitationView,
    TeacherLookupResponse,
    TeacherManagementOverviewResponse,
    UserMeResponse,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TEACHER_INVITATION_TARGET_TYPE = "teacher_invitation"
_TEACHER_INVITATION_EVENT_BATCH_SIZE = 1000


def normalize_and_validate_email(raw_email: str) -> str:
    normalized = raw_email.strip().lower()
    if len(normalized) < 5 or len(normalized) > 254 or not _EMAIL_RE.match(normalized):
        raise AppError(
            code="INVALID_EMAIL",
            message="Please enter a valid email address.",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return normalized


def hash_teacher_invite_token(raw_token: str) -> str:
    cleaned = raw_token.strip()
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def generate_teacher_invite_token() -> tuple[str, str, str]:
    raw_token = f"tfi_{secrets.token_urlsafe(32)}"
    token_hash = hash_teacher_invite_token(raw_token)
    token_preview = f"{raw_token[:8]}...{raw_token[-4:]}"
    return raw_token, token_hash, token_preview


@dataclass(slots=True)
class _FoldedInvitation:
    id: UUID
    email: str
    full_name: str
    status: TeacherInvitationStatus
    delivery_status: TeacherInvitationDeliveryStatus
    delivery_detail: str
    token_hash: str
    token_preview: str
    invited_by_id: UUID | None
    invited_by_email: str | None
    accepted_by_user_id: UUID | None
    accepted_at: datetime | None
    revoked_by_user_id: UUID | None
    revoked_at: datetime | None
    resend_count: int
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    def to_view(self) -> TeacherInvitationView:
        return TeacherInvitationView(
            id=self.id,
            email=self.email,
            full_name=self.full_name,
            status=self.status,
            delivery_status=self.delivery_status,
            delivery_detail=self.delivery_detail,
            token_preview=self.token_preview,
            invited_by_id=self.invited_by_id,
            invited_by_email=self.invited_by_email,
            accepted_by_user_id=self.accepted_by_user_id,
            accepted_at=self.accepted_at,
            revoked_by_user_id=self.revoked_by_user_id,
            revoked_at=self.revoked_at,
            resend_count=self.resend_count,
            expires_at=self.expires_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


def _parse_iso_dt(raw: object, fallback: datetime) -> datetime:
    if isinstance(raw, datetime):
        return raw if raw.tzinfo is not None else raw.replace(tzinfo=UTC)
    if isinstance(raw, str) and raw.strip():
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
        except ValueError:
            return fallback
    return fallback


def _parse_optional_uuid(raw: object) -> UUID | None:
    if isinstance(raw, UUID):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return UUID(raw.strip())
        except ValueError:
            return None
    return None


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


def _to_admin_user_summary(record: UserRecord) -> AdminUserSummary:
    return AdminUserSummary(
        id=record.id,
        email=record.email,
        full_name=record.full_name,
        roles=record.roles,
        onboarding_completed=record.onboarding_completed,
        created_at=record.created_at,
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
        items = [_to_admin_user_summary(record) for record in records]
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

    # --- Admin Teacher Management & Verified Teacher Invitations ---

    @staticmethod
    def _apply_invitation_event(
        by_id: dict[UUID, _FoldedInvitation],
        rec: AuditRecord,
        event_time: datetime,
        actor_email: str | None,
    ) -> None:
        inv_id = _parse_optional_uuid(rec.target_id)
        if inv_id is None:
            return
        meta = rec.metadata or {}
        ev_dt = event_time if event_time.tzinfo is not None else event_time.replace(tzinfo=UTC)

        if rec.action == "teacher.invitation_created":
            email = str(meta.get("email") or "").strip().lower()
            token_hash = str(meta.get("token_hash") or "").strip()
            if not email or not token_hash:
                return
            deliv_raw = str(meta.get("delivery_status") or "delivery_blocked")
            deliv_status: TeacherInvitationDeliveryStatus = (
                "sent" if deliv_raw == "sent" else "delivery_blocked"
            )
            expires_at = _parse_iso_dt(meta.get("expires_at"), ev_dt + timedelta(days=7))
            by_id[inv_id] = _FoldedInvitation(
                id=inv_id,
                email=email,
                full_name=str(meta.get("full_name") or "").strip(),
                status="pending",
                delivery_status=deliv_status,
                delivery_detail=str(
                    meta.get("delivery_detail")
                    or "Pending email delivery or direct invitation link verification."
                ),
                token_hash=token_hash,
                token_preview=str(meta.get("token_preview") or "tfi_..."),
                invited_by_id=rec.actor_user_id,
                invited_by_email=actor_email or str(meta.get("invited_by_email") or "") or None,
                accepted_by_user_id=None,
                accepted_at=None,
                revoked_by_user_id=None,
                revoked_at=None,
                resend_count=0,
                expires_at=expires_at,
                created_at=ev_dt,
                updated_at=ev_dt,
            )
        elif rec.action == "teacher.invitation_resent" and inv_id in by_id:
            inv = by_id[inv_id]
            if inv.status in ("accepted", "revoked"):
                return
            new_hash = str(meta.get("token_hash") or "").strip()
            if new_hash:
                inv.token_hash = new_hash
            new_preview = str(meta.get("token_preview") or "").strip()
            if new_preview:
                inv.token_preview = new_preview
            inv.expires_at = _parse_iso_dt(meta.get("expires_at"), ev_dt + timedelta(days=7))
            deliv_raw = str(meta.get("delivery_status") or inv.delivery_status)
            inv.delivery_status = "sent" if deliv_raw == "sent" else "delivery_blocked"
            if meta.get("delivery_detail"):
                inv.delivery_detail = str(meta["delivery_detail"])
            inv.resend_count += 1
            inv.status = "pending"
            inv.updated_at = ev_dt
        elif rec.action == "teacher.invitation_accepted" and inv_id in by_id:
            inv = by_id[inv_id]
            inv.status = "accepted"
            inv.accepted_by_user_id = (
                _parse_optional_uuid(meta.get("accepted_by_user_id")) or rec.actor_user_id
            )
            inv.accepted_at = ev_dt
            inv.updated_at = ev_dt
        elif rec.action == "teacher.invitation_revoked" and inv_id in by_id:
            inv = by_id[inv_id]
            if inv.status != "accepted":
                inv.status = "revoked"
                inv.revoked_by_user_id = rec.actor_user_id
                inv.revoked_at = ev_dt
                inv.updated_at = ev_dt

    async def _fold_teacher_invitations(
        self,
    ) -> tuple[list[_FoldedInvitation], dict[UUID, _FoldedInvitation]]:
        """Stream and fold all teacher invitation audit events in batches without truncation."""
        by_id: dict[UUID, _FoldedInvitation] = {}
        offset = 0
        while True:
            batch = await self._repo.list_audit_events_by_target_type(
                TEACHER_INVITATION_TARGET_TYPE,
                limit=_TEACHER_INVITATION_EVENT_BATCH_SIZE,
                offset=offset,
            )
            for rec, event_time, actor_email in batch:
                self._apply_invitation_event(by_id, rec, event_time, actor_email)
            if len(batch) < _TEACHER_INVITATION_EVENT_BATCH_SIZE:
                break
            offset += len(batch)

        now = datetime.now(UTC)
        for inv in by_id.values():
            if inv.status == "pending" and now >= inv.expires_at:
                inv.status = "expired"

        ordered = sorted(by_id.values(), key=lambda item: item.created_at, reverse=True)
        return ordered, by_id

    async def _fold_single_teacher_invitation(
        self, invitation_id: UUID
    ) -> _FoldedInvitation | None:
        """Fold audit events for a single invitation ID without scanning the full audit table."""
        events = await self._repo.list_audit_events_for_target(
            TEACHER_INVITATION_TARGET_TYPE, str(invitation_id)
        )
        by_id: dict[UUID, _FoldedInvitation] = {}
        for rec, event_time, actor_email in events:
            self._apply_invitation_event(by_id, rec, event_time, actor_email)
        inv = by_id.get(invitation_id)
        if inv is not None and inv.status == "pending" and datetime.now(UTC) >= inv.expires_at:
            inv.status = "expired"
        return inv

    async def get_teacher_management_overview(
        self,
        *,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
        invitations_limit: int | None = None,
        invitations_offset: int | None = None,
    ) -> TeacherManagementOverviewResponse:
        active_records, active_total = await self._repo.list_users(
            limit=limit, offset=offset, role="teacher", q=q
        )
        inv_limit = invitations_limit if invitations_limit is not None else limit
        inv_offset = invitations_offset if invitations_offset is not None else offset

        folded_invitations, _ = await self._fold_teacher_invitations()
        needle = (q or "").strip().lower()
        if needle:
            filtered_invitations = [
                inv
                for inv in folded_invitations
                if needle in inv.email.lower() or needle in inv.full_name.lower()
            ]
        else:
            filtered_invitations = folded_invitations

        invitations_total = len(filtered_invitations)
        page_invitations = filtered_invitations[inv_offset : inv_offset + inv_limit]
        pending_count = sum(1 for inv in folded_invitations if inv.status == "pending")
        return TeacherManagementOverviewResponse(
            active_teachers=[_to_admin_user_summary(r) for r in active_records],
            active_teachers_total=active_total,
            invitations=[inv.to_view() for inv in page_invitations],
            invitations_total=invitations_total,
            invitations_limit=inv_limit,
            invitations_offset=inv_offset,
            pending_invitations_count=pending_count,
        )

    async def lookup_teacher_by_email(self, *, email: str) -> TeacherLookupResponse:
        normalized = normalize_and_validate_email(email)
        existing_user = await self._repo.get_user_by_email(normalized)
        folded_invitations, _ = await self._fold_teacher_invitations()
        matching_invitations = [
            inv for inv in folded_invitations if inv.email.lower() == normalized
        ]
        latest_inv = matching_invitations[0] if matching_invitations else None

        if existing_user is not None:
            user_summary = _to_admin_user_summary(existing_user)
            if "teacher" in existing_user.roles:
                return TeacherLookupResponse(
                    email=normalized,
                    status="active_teacher",
                    can_grant_directly=False,
                    can_invite=False,
                    existing_user=user_summary,
                    latest_invitation=latest_inv.to_view() if latest_inv else None,
                    message=(
                        f"{existing_user.full_name or normalized} already holds active "
                        "Teacher access."
                    ),
                )
            return TeacherLookupResponse(
                email=normalized,
                status="existing_user_not_teacher",
                can_grant_directly=True,
                can_invite=False,
                existing_user=user_summary,
                latest_invitation=latest_inv.to_view() if latest_inv else None,
                message=(
                    f"Verified existing account found for {existing_user.full_name or normalized} "
                    f"(current roles: {', '.join(existing_user.roles)}). Confirm below to grant "
                    "the Teacher role directly."
                ),
            )

        if latest_inv is not None:
            if latest_inv.status == "pending":
                return TeacherLookupResponse(
                    email=normalized,
                    status="pending_invitation",
                    can_grant_directly=False,
                    can_invite=False,
                    existing_user=None,
                    latest_invitation=latest_inv.to_view(),
                    message=(
                        f"An active pending teacher invitation already exists for {normalized}. "
                        "You can resend or revoke the pending invitation below."
                    ),
                )
            if latest_inv.status == "expired":
                return TeacherLookupResponse(
                    email=normalized,
                    status="expired_invitation",
                    can_grant_directly=False,
                    can_invite=True,
                    existing_user=None,
                    latest_invitation=latest_inv.to_view(),
                    message=(
                        f"A previous teacher invitation for {normalized} expired. "
                        "You can resend or create a fresh invitation."
                    ),
                )
            if latest_inv.status == "revoked":
                return TeacherLookupResponse(
                    email=normalized,
                    status="revoked_invitation",
                    can_grant_directly=False,
                    can_invite=True,
                    existing_user=None,
                    latest_invitation=latest_inv.to_view(),
                    message=(
                        f"A previous teacher invitation for {normalized} was revoked. "
                        "You can issue a new invitation if authorized."
                    ),
                )

        return TeacherLookupResponse(
            email=normalized,
            status="not_found",
            can_grant_directly=False,
            can_invite=True,
            existing_user=None,
            latest_invitation=None,
            message=(
                f"No existing account found for {normalized}. You can send a secure Teacher "
                "Invitation so they can register, verify their email, and activate Teacher access."
            ),
        )

    async def create_teacher_invitation(
        self,
        *,
        actor: UserRecord,
        payload: TeacherInvitationCreateRequest,
        request_id: str | None,
        expires_at_override: datetime | None = None,
    ) -> TeacherInvitationMutationResponse:
        normalized = normalize_and_validate_email(payload.email)
        full_name = payload.full_name.strip()

        existing_user = await self._repo.get_user_by_email(normalized)
        if existing_user is not None:
            if "teacher" in existing_user.roles:
                raise AppError(
                    code="ALREADY_TEACHER",
                    message=f"{normalized} already holds the Teacher role.",
                    status_code=status.HTTP_409_CONFLICT,
                )
            raise AppError(
                code="EXISTING_ACCOUNT_FOUND",
                message=(
                    f"An account for {normalized} already exists. Please use 'Add Existing "
                    "Teacher' to confirm and grant the Teacher role directly."
                ),
                status_code=status.HTTP_409_CONFLICT,
                details={"user_id": str(existing_user.id), "email": existing_user.email},
            )

        folded_invitations, _ = await self._fold_teacher_invitations()
        for inv in folded_invitations:
            if inv.email.lower() == normalized and inv.status == "pending":
                raise AppError(
                    code="DUPLICATE_PENDING_INVITATION",
                    message=(
                        f"An active pending teacher invitation already exists for {normalized}. "
                        "Use 'Resend Invitation' instead of creating a duplicate."
                    ),
                    status_code=status.HTTP_409_CONFLICT,
                    details={"invitation_id": str(inv.id)},
                )

        raw_token, token_hash, token_preview = generate_teacher_invite_token()
        now = datetime.now(UTC)
        expires_at = expires_at_override or (now + timedelta(days=payload.expires_in_days))
        inv_id = uuid4()

        # Honestly report delivery status: without a configured outbound SMTP / service-role mailer
        # on the API server, we record 'delivery_blocked' rather than pretending an email was sent,
        # and provide the verified one-time acceptance path.
        delivery_status: TeacherInvitationDeliveryStatus = "delivery_blocked"
        delivery_detail = (
            "Automated SMTP invitation email delivery is not configured on the API server "
            "(Pending / Delivery Blocked). Share the one-time verified invitation link with the "
            "instructor so they can verify their email and activate Teacher access."
        )

        await self._repo.record_audit_log(
            AuditRecord(
                actor_user_id=actor.id,
                action="teacher.invitation_created",
                target_type=TEACHER_INVITATION_TARGET_TYPE,
                target_id=str(inv_id),
                metadata={
                    "email": normalized,
                    "full_name": full_name,
                    "role": "teacher",
                    "token_hash": token_hash,
                    "token_preview": token_preview,
                    "delivery_status": delivery_status,
                    "delivery_detail": delivery_detail,
                    "invited_by_email": actor.email,
                    "expires_at": expires_at.isoformat(),
                },
                request_id=request_id,
            )
        )

        created_status: TeacherInvitationStatus = "expired" if now >= expires_at else "pending"
        created = _FoldedInvitation(
            id=inv_id,
            email=normalized,
            full_name=full_name,
            status=created_status,
            delivery_status=delivery_status,
            delivery_detail=delivery_detail,
            token_hash=token_hash,
            token_preview=token_preview,
            invited_by_id=actor.id,
            invited_by_email=actor.email,
            accepted_by_user_id=None,
            accepted_at=None,
            revoked_by_user_id=None,
            revoked_at=None,
            resend_count=0,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )

        return TeacherInvitationMutationResponse(
            invitation=created.to_view(),
            invitation_token=raw_token,
            accept_path=f"/accept-teacher-invite?token={raw_token}",
            action="teacher.invitation_created",
        )

    async def resend_teacher_invitation(
        self,
        *,
        actor: UserRecord,
        invitation_id: UUID,
        request_id: str | None,
    ) -> TeacherInvitationMutationResponse:
        inv = await self._fold_single_teacher_invitation(invitation_id)
        if inv is None:
            raise AppError(
                code="INVITATION_NOT_FOUND",
                message="Teacher invitation was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if inv.status == "accepted":
            raise AppError(
                code="INVITATION_ALREADY_ACCEPTED",
                message="This teacher invitation has already been accepted.",
                status_code=status.HTTP_409_CONFLICT,
            )
        if inv.status == "revoked":
            raise AppError(
                code="INVITATION_REVOKED",
                message="Cannot resend a revoked teacher invitation. Create a new invitation.",
                status_code=status.HTTP_409_CONFLICT,
            )

        raw_token, token_hash, token_preview = generate_teacher_invite_token()
        now = datetime.now(UTC)
        new_expires_at = now + timedelta(days=7)
        delivery_status: TeacherInvitationDeliveryStatus = "delivery_blocked"
        delivery_detail = (
            "Invitation token rotated and expiration extended by 7 days "
            "(SMTP Delivery Blocked — share the refreshed one-time invitation link)."
        )

        await self._repo.record_audit_log(
            AuditRecord(
                actor_user_id=actor.id,
                action="teacher.invitation_resent",
                target_type=TEACHER_INVITATION_TARGET_TYPE,
                target_id=str(invitation_id),
                metadata={
                    "email": inv.email,
                    "token_hash": token_hash,
                    "token_preview": token_preview,
                    "delivery_status": delivery_status,
                    "delivery_detail": delivery_detail,
                    "expires_at": new_expires_at.isoformat(),
                },
                request_id=request_id,
            )
        )

        inv.token_hash = token_hash
        inv.token_preview = token_preview
        inv.expires_at = new_expires_at
        inv.delivery_status = delivery_status
        inv.delivery_detail = delivery_detail
        inv.resend_count += 1
        inv.status = "pending"
        inv.updated_at = now
        return TeacherInvitationMutationResponse(
            invitation=inv.to_view(),
            invitation_token=raw_token,
            accept_path=f"/accept-teacher-invite?token={raw_token}",
            action="teacher.invitation_resent",
        )

    async def revoke_teacher_invitation(
        self,
        *,
        actor: UserRecord,
        invitation_id: UUID,
        request_id: str | None,
    ) -> TeacherInvitationMutationResponse:
        inv = await self._fold_single_teacher_invitation(invitation_id)
        if inv is None:
            raise AppError(
                code="INVITATION_NOT_FOUND",
                message="Teacher invitation was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if inv.status == "accepted":
            raise AppError(
                code="INVITATION_ALREADY_ACCEPTED",
                message=(
                    "This invitation was already accepted. Revoke the user's Teacher role "
                    "from Active Teachers instead."
                ),
                status_code=status.HTTP_409_CONFLICT,
            )

        now = datetime.now(UTC)
        await self._repo.record_audit_log(
            AuditRecord(
                actor_user_id=actor.id,
                action="teacher.invitation_revoked",
                target_type=TEACHER_INVITATION_TARGET_TYPE,
                target_id=str(invitation_id),
                metadata={"email": inv.email},
                request_id=request_id,
            )
        )

        inv.status = "revoked"
        inv.revoked_by_user_id = actor.id
        inv.revoked_at = now
        inv.updated_at = now
        return TeacherInvitationMutationResponse(
            invitation=inv.to_view(),
            invitation_token=None,
            accept_path=None,
            action="teacher.invitation_revoked",
        )

    async def _find_invitation_by_token(self, raw_token: str) -> _FoldedInvitation | None:
        cleaned = raw_token.strip()
        if len(cleaned) < 16:
            return None
        candidate_hash = hash_teacher_invite_token(cleaned)
        folded, _ = await self._fold_teacher_invitations()
        for inv in folded:
            if hmac.compare_digest(inv.token_hash, candidate_hash):
                return inv
        return None

    async def inspect_teacher_invitation(
        self, *, raw_token: str
    ) -> TeacherInvitationInspectResponse:
        inv = await self._find_invitation_by_token(raw_token)
        if inv is None:
            raise AppError(
                code="INVITATION_INVALID",
                message="Invalid or unrecognized teacher invitation token.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if inv.status == "revoked":
            msg = "This teacher invitation has been revoked by an administrator."
        elif inv.status == "accepted":
            msg = "This teacher invitation has already been accepted."
        elif inv.status == "expired":
            msg = "This teacher invitation has expired. Please ask an administrator to resend it."
        else:
            msg = (
                f"Valid teacher invitation for {inv.email}. Sign in or register with this "
                "exact email address to activate Teacher access."
            )

        return TeacherInvitationInspectResponse(
            invitation_id=inv.id,
            email=inv.email,
            full_name=inv.full_name,
            status=inv.status,
            expires_at=inv.expires_at,
            is_valid=inv.status == "pending",
            message=msg,
        )

    async def accept_teacher_invitation(
        self,
        *,
        user: UserRecord,
        raw_token: str,
        request_id: str | None,
    ) -> TeacherInvitationAcceptResponse:
        inv = await self._find_invitation_by_token(raw_token)
        if inv is None:
            raise AppError(
                code="INVITATION_INVALID",
                message="Invalid or unrecognized teacher invitation token.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if inv.status == "revoked":
            raise AppError(
                code="INVITATION_REVOKED",
                message="This teacher invitation was revoked by an administrator.",
                status_code=status.HTTP_410_GONE,
            )

        if inv.status == "accepted":
            raise AppError(
                code="INVITATION_ALREADY_USED",
                message="This teacher invitation has already been accepted and cannot be reused.",
                status_code=status.HTTP_409_CONFLICT,
            )

        if inv.status == "expired" or datetime.now(UTC) >= inv.expires_at:
            raise AppError(
                code="INVITATION_EXPIRED",
                message=(
                    "This teacher invitation has expired. Please ask an administrator to resend it."
                ),
                status_code=status.HTTP_410_GONE,
            )

        if user.email.strip().lower() != inv.email.strip().lower():
            await self._repo.record_audit_log(
                AuditRecord(
                    actor_user_id=user.id,
                    action="teacher.invitation_denied",
                    target_type=TEACHER_INVITATION_TARGET_TYPE,
                    target_id=str(inv.id),
                    metadata={
                        "invited_email": inv.email,
                        "attempted_by_email": user.email,
                        "reason": "email_mismatch",
                    },
                    request_id=request_id,
                )
            )
            raise AppError(
                code="INVITATION_EMAIL_MISMATCH",
                message=(
                    f"This teacher invitation was issued to {inv.email}, but you are signed in "
                    f"as {user.email}. Sign in with {inv.email} to accept it."
                ),
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Grant ONLY the 'teacher' role (NEVER 'admin'), preserving existing legitimate roles
        grant_actor_id = inv.invited_by_id or user.id
        updated_roles = await self._repo.grant_role(
            user_id=user.id,
            role="teacher",
            granted_by=grant_actor_id,
        )

        await self._repo.record_audit_log(
            AuditRecord(
                actor_user_id=user.id,
                action="teacher.invitation_accepted",
                target_type=TEACHER_INVITATION_TARGET_TYPE,
                target_id=str(inv.id),
                metadata={
                    "email": inv.email,
                    "accepted_by_user_id": str(user.id),
                    "granted_role": "teacher",
                    "resulting_roles": updated_roles,
                },
                request_id=request_id,
            )
        )
        await self._repo.record_audit_log(
            AuditRecord(
                actor_user_id=grant_actor_id,
                action="role.granted",
                target_type="user",
                target_id=str(user.id),
                metadata={
                    "role": "teacher",
                    "source": "teacher_invitation",
                    "invitation_id": str(inv.id),
                    "resulting_roles": updated_roles,
                },
                request_id=request_id,
            )
        )

        reloaded = await self._repo.get_user_by_id(user.id)
        if reloaded is None:
            raise RuntimeError("Failed to reload user after accepting teacher invitation")

        return TeacherInvitationAcceptResponse(
            invitation_id=inv.id,
            user=_to_user_me_response(reloaded),
            action="teacher.invitation_accepted",
        )
