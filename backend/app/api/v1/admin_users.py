from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.v1.deps import get_identity_service, require_roles
from app.repositories.identity import UserRecord
from app.schemas.common import PaginatedResponse
from app.schemas.identity import (
    AdminRoleMutationRequest,
    AdminRoleMutationResponse,
    AdminUserSummary,
    RoleName,
)
from app.services.identity.service import IdentityService

admin_users_router = APIRouter(prefix="/admin/users", tags=["Admin Users & Roles"])


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
