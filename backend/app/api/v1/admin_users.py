from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.v1.deps import get_identity_service, require_roles
from app.repositories.identity import UserRecord
from app.schemas.common import PaginatedResponse
from app.schemas.identity import (
    AdminRoleMutationRequest,
    AdminRoleMutationResponse,
    AdminUserSummary,
    RoleName,
    TeacherInvitationCreateRequest,
    TeacherInvitationMutationResponse,
    TeacherLookupResponse,
    TeacherManagementOverviewResponse,
)
from app.services.identity.service import IdentityService

admin_users_router = APIRouter(prefix="/admin/users", tags=["Admin Users & Roles"])
admin_teachers_router = APIRouter(prefix="/admin/teachers", tags=["Admin Teacher Management"])


@admin_users_router.get("", response_model=PaginatedResponse[AdminUserSummary])
async def list_admin_users(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    role: RoleName | None = Query(default=None),
    q: str | None = Query(default=None, max_length=120),
    _admin_user: UserRecord = Depends(require_roles("admin")),
    service: IdentityService = Depends(get_identity_service),
) -> PaginatedResponse[AdminUserSummary]:
    """List users and their DB-backed roles (Admin only)."""
    return await service.list_users(limit=limit, offset=offset, role=role, q=q)


@admin_users_router.post("/{user_id}/roles", response_model=AdminRoleMutationResponse)
async def grant_user_role(
    user_id: UUID,
    payload: AdminRoleMutationRequest,
    request: Request,
    admin_user: UserRecord = Depends(require_roles("admin")),
    service: IdentityService = Depends(get_identity_service),
) -> AdminRoleMutationResponse:
    """Grant a role to a user (Admin only, audited)."""
    request_id = getattr(request.state, "request_id", None)
    return await service.grant_role(
        actor=admin_user,
        target_user_id=user_id,
        role=payload.role,
        request_id=request_id,
    )


@admin_users_router.delete("/{user_id}/roles/{role}", response_model=AdminRoleMutationResponse)
async def revoke_user_role(
    user_id: UUID,
    role: RoleName,
    request: Request,
    admin_user: UserRecord = Depends(require_roles("admin")),
    service: IdentityService = Depends(get_identity_service),
) -> AdminRoleMutationResponse:
    """Revoke a role from a user (Admin only, last-admin protected, audited)."""
    request_id = getattr(request.state, "request_id", None)
    return await service.revoke_role(
        actor=admin_user,
        target_user_id=user_id,
        role=role,
        request_id=request_id,
    )


@admin_teachers_router.get("", response_model=TeacherManagementOverviewResponse)
async def get_admin_teacher_management(
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    invitations_limit: int | None = Query(default=None, ge=1, le=100),
    invitations_offset: int | None = Query(default=None, ge=0),
    _admin_user: UserRecord = Depends(require_roles("admin")),
    service: IdentityService = Depends(get_identity_service),
) -> TeacherManagementOverviewResponse:
    """List active Teachers and pending/historical Teacher Invitations (Admin only)."""
    return await service.get_teacher_management_overview(
        q=q,
        limit=limit,
        offset=offset,
        invitations_limit=invitations_limit,
        invitations_offset=invitations_offset,
    )


@admin_teachers_router.get("/lookup", response_model=TeacherLookupResponse)
async def lookup_admin_teacher_by_email(
    email: str = Query(..., min_length=3, max_length=254),
    _admin_user: UserRecord = Depends(require_roles("admin")),
    service: IdentityService = Depends(get_identity_service),
) -> TeacherLookupResponse:
    """Check if an email belongs to an active teacher, an existing user, or a pending invite."""
    return await service.lookup_teacher_by_email(email=email)


@admin_teachers_router.post(
    "/invitations",
    response_model=TeacherInvitationMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_teacher_invitation(
    payload: TeacherInvitationCreateRequest,
    request: Request,
    admin_user: UserRecord = Depends(require_roles("admin")),
    service: IdentityService = Depends(get_identity_service),
) -> TeacherInvitationMutationResponse:
    """Create a secure pending Teacher Invitation for a new instructor email (Admin only)."""
    request_id = getattr(request.state, "request_id", None)
    return await service.create_teacher_invitation(
        actor=admin_user,
        payload=payload,
        request_id=request_id,
    )


@admin_teachers_router.post(
    "/invitations/{invitation_id}/resend",
    response_model=TeacherInvitationMutationResponse,
)
async def resend_admin_teacher_invitation(
    invitation_id: UUID,
    request: Request,
    admin_user: UserRecord = Depends(require_roles("admin")),
    service: IdentityService = Depends(get_identity_service),
) -> TeacherInvitationMutationResponse:
    """Rotate token and resend/extend a pending or expired Teacher Invitation (Admin only)."""
    request_id = getattr(request.state, "request_id", None)
    return await service.resend_teacher_invitation(
        actor=admin_user,
        invitation_id=invitation_id,
        request_id=request_id,
    )


@admin_teachers_router.delete(
    "/invitations/{invitation_id}",
    response_model=TeacherInvitationMutationResponse,
)
async def revoke_admin_teacher_invitation(
    invitation_id: UUID,
    request: Request,
    admin_user: UserRecord = Depends(require_roles("admin")),
    service: IdentityService = Depends(get_identity_service),
) -> TeacherInvitationMutationResponse:
    """Revoke a pending Teacher Invitation so its token can never be accepted (Admin only)."""
    request_id = getattr(request.state, "request_id", None)
    return await service.revoke_teacher_invitation(
        actor=admin_user,
        invitation_id=invitation_id,
        request_id=request_id,
    )
