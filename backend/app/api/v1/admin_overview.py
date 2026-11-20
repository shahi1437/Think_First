"""Admin-only Phase 8 Overview, Audit Log & Phase 9 Operations Health routes."""

import time

import httpx
from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import (
    get_admin_overview_service,
    get_ml_classifier_service,
    require_roles,
)
from app.core.config import Settings, get_settings
from app.core.database import DatabaseManager, get_db_manager
from app.core.errors import AppError
from app.integrations.judge0.client import build_judge0_auth_headers, is_judge0_configured
from app.repositories.identity import UserRecord
from app.schemas.admin import (
    AdminAuditLogItem,
    AdminDashboardOverview,
    AdminOperationsHealthResponse,
    OperationalCheckStatus,
)
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


@admin_overview_router.get("/operations/health", response_model=AdminOperationsHealthResponse)
async def get_admin_operations_health(
    _admin: UserRecord = Depends(require_roles("admin")),
    settings: Settings = Depends(get_settings),
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> AdminOperationsHealthResponse:
    """Measure live PostgreSQL, ML artifact, Judge0 CE, and LLM readiness without leaking keys."""
    checks: list[OperationalCheckStatus] = []

    db_start = time.perf_counter()
    db_ok = await db_manager.check_health()
    db_latency = round((time.perf_counter() - db_start) * 1000, 2)
    checks.append(
        OperationalCheckStatus(
            name="postgresql",
            status="ok" if db_ok else "unavailable",
            latency_ms=db_latency,
            detail="Primary PostgreSQL + pgvector connection healthy."
            if db_ok
            else "Database connectivity check failed.",
        )
    )

    ml_status = get_ml_classifier_service(settings).get_status_summary()
    checks.append(
        OperationalCheckStatus(
            name="ml_classifier",
            status="ok" if ml_status["loaded"] else "degraded",
            latency_ms=None,
            detail=(
                f"version={ml_status['model_version']} "
                f"artifact_exists={ml_status['artifact_exists']}"
            ),
        )
    )

    judge0_ok = False
    judge0_latency: float | None = None
    judge0_detail = "Judge0 endpoint unreachable."
    j_start = time.perf_counter()
    if not is_judge0_configured(settings):
        judge0_latency = 0.0
        judge0_detail = "Judge0 CE is disabled or not configured yet (code execution unavailable)."
    else:
        try:
            headers = build_judge0_auth_headers(settings) or None
            async with httpx.AsyncClient(timeout=2.5) as client:
                resp = await client.get(
                    f"{settings.judge0_base_url.rstrip('/')}/about",
                    headers=headers,
                )
                judge0_latency = round((time.perf_counter() - j_start) * 1000, 2)
                if resp.status_code == 200:
                    judge0_ok = True
                    version = resp.json().get("version", "unknown")
                    judge0_detail = f"Judge0 CE online (version={version})."
                else:
                    judge0_detail = f"Judge0 CE returned HTTP {resp.status_code}."
        except AppError as exc:
            judge0_latency = round((time.perf_counter() - j_start) * 1000, 2)
            judge0_detail = exc.message
        except Exception as exc:
            judge0_latency = round((time.perf_counter() - j_start) * 1000, 2)
            judge0_detail = f"Judge0 check failed ({type(exc).__name__})."

    checks.append(
        OperationalCheckStatus(
            name="judge0",
            status="ok" if judge0_ok else "unavailable",
            latency_ms=judge0_latency,
            detail=judge0_detail,
        )
    )

    has_live_llm = (
        settings.llm_provider != "none"
        and bool(settings.llm_api_key and settings.llm_api_key.strip())
        and bool(settings.llm_model.strip())
    )
    llm_mode = "live_llm" if has_live_llm else "deterministic_fallback"
    llm_model_label = settings.llm_model.strip() or "none"
    checks.append(
        OperationalCheckStatus(
            name="socratic_llm",
            status="ok" if has_live_llm else "degraded",
            latency_ms=None,
            detail=f"provider={settings.llm_provider} mode={llm_mode}",
        )
    )

    overall_ok = all(
        check.status == "ok" for check in checks if check.name in {"postgresql", "judge0"}
    )
    return AdminOperationsHealthResponse(
        overall_status="ok" if overall_ok else "degraded",
        environment=settings.app_env,
        rate_limit_enabled=settings.rate_limit_enabled,
        llm_provider_mode=llm_mode,
        llm_provider=settings.llm_provider,
        llm_model=llm_model_label,
        checks=checks,
    )


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
