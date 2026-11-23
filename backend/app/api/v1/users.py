from fastapi import APIRouter, Depends, Query, Request

from app.api.v1.deps import get_current_user, get_identity_service, require_roles
from app.repositories.identity import UserRecord
from app.schemas.identity import (
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
