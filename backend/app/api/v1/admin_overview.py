"""Admin-only Phase 8 Overview & Immutable Audit Log routes."""

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import get_admin_overview_service, require_roles
from app.repositories.identity import UserRecord
from app.schemas.admin import AdminAuditLogItem, AdminDashboardOverview
from app.schemas.common import PaginatedResponse
from app.services.admin.overview_service import AdminOverviewService

admin_overview_router = APIRouter(prefix="/admin", tags=["Admin Dashboard & Audit"])


@admin_overview_router.get("/overview", response_model=AdminDashboardOverview)
async def get_admin_overview(
    _admin: UserRecord = Depends(require_roles("admin")),
    service: AdminOverviewService = Depends(get_admin_overview_service),
) -> AdminDashboardOverview:
    """Return real DB metrics, review queue, curriculum coverage, and audit trail."""
    return await service.get_overview()


@admin_overview_router.get("/audit-logs", response_model=PaginatedResponse[AdminAuditLogItem])
async def list_admin_audit_logs(
    action_prefix: str | None = Query(default=None, max_length=64),
    target_type: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=40, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _admin: UserRecord = Depends(require_roles("admin")),
    service: AdminOverviewService = Depends(get_admin_overview_service),
) -> PaginatedResponse[AdminAuditLogItem]:
    """List immutable admin/content audit events with actor resolution."""
    return await service.list_audit_logs(
        action_prefix=action_prefix,
        target_type=target_type,
        limit=limit,
        offset=offset,
    )
