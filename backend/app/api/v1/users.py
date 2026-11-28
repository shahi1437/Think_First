from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_identity_service, require_roles
from app.core.database import get_db_session
from app.models.identity import AuditLog
from app.models.mentor import LearningEvent
from app.repositories.identity import UserRecord
from app.schemas.identity import (
    MlDataConsentResponse,
    MlDataConsentUpdateRequest,
    OnboardingSubmitRequest,
    PortalVerifyRequest,
    TeacherInvitationAcceptRequest,
    TeacherInvitationAcceptResponse,
    TeacherInvitationInspectResponse,
    TeacherScopeResponse,
    UserMeResponse,
    UserPreferencesUpdate,
)
from app.services.identity.service import IdentityService

ML_DATA_CONSENT_EVENT_TYPE = "ml_data_consent_updated"
ML_DATA_CONSENT_SCOPE = "anonymized_python_debugging_events"

users_router = APIRouter(prefix="/users", tags=["Identity & Onboarding"])
teacher_identity_router = APIRouter(prefix="/teacher", tags=["Teacher"])


@users_router.get("/me", response_model=UserMeResponse)
async def get_users_me(
    current_user: UserRecord = Depends(get_current_user),
    service: IdentityService = Depends(get_identity_service),
) -> UserMeResponse:
    """Return the authenticated user's profile, DB-backed roles, and preferences."""
    return await service.get_me(current_user)


@users_router.post("/me/verify-portal", response_model=UserMeResponse)
async def post_users_me_verify_portal(
    payload: PortalVerifyRequest,
    request: Request,
    current_user: UserRecord = Depends(get_current_user),
    service: IdentityService = Depends(get_identity_service),
) -> UserMeResponse:
    """Verify DB-backed role authorization for a specific login portal."""
    request_id = getattr(request.state, "request_id", None)
    return await service.verify_login_portal(
        user=current_user,
        portal=payload.portal,
        request_id=request_id,
    )


@users_router.post("/me/onboarding", response_model=UserMeResponse)
async def post_users_me_onboarding(
    payload: OnboardingSubmitRequest,
    current_user: UserRecord = Depends(get_current_user),
    service: IdentityService = Depends(get_identity_service),
) -> UserMeResponse:
    """Persist smart onboarding inputs and compute initial entry track."""
    return await service.complete_onboarding(user=current_user, payload=payload)


@users_router.patch("/me/preferences", response_model=UserMeResponse)
async def patch_users_me_preferences(
    payload: UserPreferencesUpdate,
    current_user: UserRecord = Depends(get_current_user),
    service: IdentityService = Depends(get_identity_service),
) -> UserMeResponse:
    """Update authenticated user's learning preferences."""
    return await service.update_preferences(user=current_user, payload=payload)


@users_router.get("/me/ml-consent", response_model=MlDataConsentResponse)
async def get_users_me_ml_consent(
    current_user: UserRecord = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MlDataConsentResponse:
    """Return the user's current opt-in consent state for anonymized ML debugging datasets."""
    stmt = (
        select(LearningEvent)
        .where(
            LearningEvent.student_id == current_user.id,
            LearningEvent.event_type == ML_DATA_CONSENT_EVENT_TYPE,
        )
        .order_by(LearningEvent.created_at.desc())
        .limit(1)
    )
    latest = (await session.execute(stmt)).scalar_one_or_none()
    if latest is None:
        return MlDataConsentResponse(
            consent_granted=False,
            policy_version="v1",
            scope=ML_DATA_CONSENT_SCOPE,
            updated_at=None,
        )
    meta = latest.metadata_json or {}
    return MlDataConsentResponse(
        consent_granted=bool(meta.get("consent_granted", False)),
        policy_version=str(meta.get("policy_version", "v1")),
        scope=str(meta.get("scope", ML_DATA_CONSENT_SCOPE)),
        updated_at=latest.created_at,
    )


@users_router.put("/me/ml-consent", response_model=MlDataConsentResponse)
async def put_users_me_ml_consent(
    payload: MlDataConsentUpdateRequest,
    request: Request,
    current_user: UserRecord = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MlDataConsentResponse:
    """Record explicit opt-in or revocation of anonymized ML debugging data collection."""
    event = LearningEvent(
        student_id=current_user.id,
        event_type=ML_DATA_CONSENT_EVENT_TYPE,
        metadata_json={
            "consent_granted": payload.consent_granted,
            "policy_version": payload.policy_version,
            "scope": ML_DATA_CONSENT_SCOPE,
        },
    )
    session.add(event)
    session.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="user.ml_consent_updated",
            target_type="user_ml_consent",
            target_id=str(current_user.id),
            metadata_json={
                "consent_granted": payload.consent_granted,
                "policy_version": payload.policy_version,
                "scope": ML_DATA_CONSENT_SCOPE,
            },
            request_id=getattr(request.state, "request_id", None),
        )
    )
    await session.commit()
    await session.refresh(event)
    return MlDataConsentResponse(
        consent_granted=payload.consent_granted,
        policy_version=payload.policy_version,
        scope=ML_DATA_CONSENT_SCOPE,
        updated_at=event.created_at,
    )


@users_router.get(
    "/teacher-invitations/inspect",
    response_model=TeacherInvitationInspectResponse,
)
async def get_inspect_teacher_invitation(
    token: str = Query(..., min_length=16, max_length=256),
    service: IdentityService = Depends(get_identity_service),
) -> TeacherInvitationInspectResponse:
    """Inspect a teacher invitation token prior to acceptance."""
    return await service.inspect_teacher_invitation(raw_token=token)


@users_router.post(
    "/me/accept-teacher-invitation",
    response_model=TeacherInvitationAcceptResponse,
)
async def post_accept_teacher_invitation(
    payload: TeacherInvitationAcceptRequest,
    request: Request,
    current_user: UserRecord = Depends(get_current_user),
    service: IdentityService = Depends(get_identity_service),
) -> TeacherInvitationAcceptResponse:
    """Accept a verified teacher invitation token and activate DB-backed Teacher role."""
    request_id = getattr(request.state, "request_id", None)
    return await service.accept_teacher_invitation(
        user=current_user,
        raw_token=payload.token,
        request_id=request_id,
    )


@teacher_identity_router.get("/me", response_model=TeacherScopeResponse)
async def get_teacher_me(
    teacher_user: UserRecord = Depends(require_roles("teacher", "admin")),
) -> TeacherScopeResponse:
    """Verify Teacher (or Admin) DB-backed role access."""
    return TeacherScopeResponse(
        user_id=teacher_user.id,
        email=teacher_user.email,
        roles=teacher_user.roles,
    )
