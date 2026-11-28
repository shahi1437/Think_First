"""Admin-only Phase 8 Overview, Audit Log & Phase 9 Operations Health routes."""

import asyncio
import time
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.api.v1.deps import (
    get_admin_overview_service,
    get_ml_classifier_service,
    require_roles,
)
from app.core.config import Settings, get_settings
from app.core.database import DatabaseManager, get_db_manager
from app.core.errors import AppError
from app.integrations.judge0.client import build_judge0_auth_headers, is_judge0_configured
from app.integrations.piston.client import is_piston_configured
from app.models.mentor import ErrorDiagnosis
from app.models.notifications import UserNotification
from app.models.problems import Submission
from app.repositories.execution_queue import ExecutionQueueRepository
from app.repositories.identity import UserRecord
from app.schemas.admin import (
    AdminAuditLogItem,
    AdminDashboardOverview,
    AdminExecutionFailureStats,
    AdminOperationsHealthResponse,
    AdminUserActivityOverview,
    OperationalCheckStatus,
)
from app.schemas.common import PaginatedResponse
from app.services.admin.overview_service import AdminOverviewService
from app.services.execution.worker_service import is_worker_queue_mode

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

    async def _probe_db() -> tuple[bool, OperationalCheckStatus]:
        db_start = time.perf_counter()
        ok = await db_manager.check_health()
        lat = round((time.perf_counter() - db_start) * 1000, 2)
        return ok, OperationalCheckStatus(
            name="postgresql",
            status="ok" if ok else "unavailable",
            latency_ms=lat,
            detail="Primary PostgreSQL + pgvector connection healthy."
            if ok
            else "Database connectivity check failed.",
        )

    async def _probe_judge0() -> tuple[bool, OperationalCheckStatus]:
        ok = False
        lat: float | None = None
        detail = "Judge0 endpoint unreachable."
        j_start = time.perf_counter()
        if is_worker_queue_mode(settings):
            try:
                async for db_sess in db_manager.session():
                    q_repo = ExecutionQueueRepository(db_sess)
                    active_workers, _, q_depth = await q_repo.get_online_workers_summary(
                        heartbeat_ttl_seconds=settings.execution_worker_heartbeat_ttl_seconds
                    )
                    lat = round((time.perf_counter() - j_start) * 1000, 2)
                    ok = active_workers > 0
                    detail = (
                        f"Outbound local Judge0 worker online "
                        f"(workers={active_workers}, queue={q_depth})."
                        if ok
                        else f"Outbound local Judge0 worker offline (queue={q_depth})."
                    )
                    break
            except Exception as exc:
                lat = round((time.perf_counter() - j_start) * 1000, 2)
                detail = f"Worker queue health check failed ({type(exc).__name__})."
        elif not is_judge0_configured(settings):
            lat = 0.0
            detail = "Judge0 CE is disabled or not configured yet (code execution unavailable)."
        else:
            try:
                headers = build_judge0_auth_headers(settings) or None
                async with httpx.AsyncClient(timeout=1.5) as client:
                    resp = await client.get(
                        f"{settings.judge0_base_url.rstrip('/')}/about",
                        headers=headers,
                    )
                    lat = round((time.perf_counter() - j_start) * 1000, 2)
                    if resp.status_code == 200:
                        ok = True
                        version = resp.json().get("version", "unknown")
                        detail = f"Judge0 CE online (version={version})."
                    else:
                        detail = f"Judge0 CE returned HTTP {resp.status_code}."
            except AppError as exc:
                lat = round((time.perf_counter() - j_start) * 1000, 2)
                detail = exc.message
            except Exception as exc:
                lat = round((time.perf_counter() - j_start) * 1000, 2)
                detail = f"Judge0 check failed ({type(exc).__name__})."
        return ok, OperationalCheckStatus(
            name="judge0",
            status="ok" if ok else "unavailable",
            latency_ms=lat,
            detail=detail,
        )

    async def _probe_piston() -> tuple[bool, OperationalCheckStatus]:
        ok = False
        lat: float | None = None
        detail = "Piston fallback disabled."
        p_start = time.perf_counter()
        if not is_piston_configured(settings):
            lat = 0.0
        else:
            try:
                async with httpx.AsyncClient(timeout=1.2) as client:
                    p_resp = await client.get(
                        f"{settings.piston_base_url.rstrip('/')}/api/v2/runtimes"
                    )
                    lat = round((time.perf_counter() - p_start) * 1000, 2)
                    if p_resp.status_code == 200:
                        runtimes = p_resp.json()
                        rt_count = len(runtimes) if isinstance(runtimes, list) else 0
                        ok = rt_count > 0
                        detail = (
                            f"Self-hosted Piston online ({rt_count} runtime(s) installed)."
                            if ok
                            else "Piston online but no language runtimes installed yet."
                        )
                    else:
                        detail = f"Piston returned HTTP {p_resp.status_code}."
            except Exception as exc:
                lat = round((time.perf_counter() - p_start) * 1000, 2)
                detail = f"Piston check failed ({type(exc).__name__})."
        piston_status = (
            "ok" if ok else ("degraded" if is_piston_configured(settings) else "unavailable")
        )
        return ok, OperationalCheckStatus(
            name="piston_fallback",
            status=piston_status,
            latency_ms=lat,
            detail=detail,
        )

    (db_ok, db_check), (judge0_ok, judge0_check), (piston_ok, piston_check) = await asyncio.gather(
        _probe_db(),
        _probe_judge0(),
        _probe_piston(),
    )

    ml_status = get_ml_classifier_service(settings).get_status_summary()
    ml_check = OperationalCheckStatus(
        name="ml_classifier",
        status="ok" if ml_status["loaded"] else "degraded",
        latency_ms=None,
        detail=(
            f"version={ml_status['model_version']} artifact_exists={ml_status['artifact_exists']}"
        ),
    )
    checks.extend([db_check, ml_check, judge0_check, piston_check])

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

    # Aggregate execution failure telemetry & anonymized user activity (zero PII / secrets)
    exec_stats: AdminExecutionFailureStats | None = None
    activity_overview: AdminUserActivityOverview | None = None
    if db_ok:
        try:
            now_utc = datetime.now(UTC)
            since_7d = now_utc - timedelta(days=7)
            since_24h = now_utc - timedelta(hours=24)
            async for db_sess in db_manager.session():
                verdict_rows = (
                    await db_sess.execute(
                        select(Submission.verdict, func.count(Submission.id))
                        .where(Submission.created_at >= since_7d)
                        .group_by(Submission.verdict)
                    )
                ).all()
                verdict_counts = {str(v): int(c) for v, c in verdict_rows}
                total_exec = sum(verdict_counts.values())
                acc_exec = verdict_counts.get("accepted", 0)
                failed_exec = max(0, total_exec - acc_exec)
                fail_rate = round((failed_exec / total_exec) * 100.0, 1) if total_exec > 0 else None

                lang_fail_rows = (
                    await db_sess.execute(
                        select(Submission.language_slug, func.count(Submission.id))
                        .where(
                            Submission.created_at >= since_7d,
                            Submission.verdict != "accepted",
                        )
                        .group_by(Submission.language_slug)
                    )
                ).all()
                failures_by_lang = {str(lg): int(c) for lg, c in lang_fail_rows}
                exec_stats = AdminExecutionFailureStats(
                    window_days=7,
                    total_executions=total_exec,
                    accepted_executions=acc_exec,
                    failed_executions=failed_exec,
                    failure_rate_pct=fail_rate,
                    verdict_counts=verdict_counts,
                    failures_by_language=failures_by_lang,
                )

                active_24h = int(
                    (
                        await db_sess.execute(
                            select(func.count(func.distinct(Submission.student_id))).where(
                                Submission.created_at >= since_24h
                            )
                        )
                    ).scalar_one()
                    or 0
                )
                active_7d = int(
                    (
                        await db_sess.execute(
                            select(func.count(func.distinct(Submission.student_id))).where(
                                Submission.created_at >= since_7d
                            )
                        )
                    ).scalar_one()
                    or 0
                )
                subs_24h = int(
                    (
                        await db_sess.execute(
                            select(func.count(Submission.id)).where(
                                Submission.created_at >= since_24h
                            )
                        )
                    ).scalar_one()
                    or 0
                )
                diags_24h = int(
                    (
                        await db_sess.execute(
                            select(func.count(ErrorDiagnosis.id)).where(
                                ErrorDiagnosis.created_at >= since_24h
                            )
                        )
                    ).scalar_one()
                    or 0
                )
                notifs_total = int(
                    (await db_sess.execute(select(func.count(UserNotification.id)))).scalar_one()
                    or 0
                )
                activity_overview = AdminUserActivityOverview(
                    active_learners_24h=active_24h,
                    active_learners_7d=active_7d,
                    submissions_24h=subs_24h,
                    diagnoses_24h=diags_24h,
                    notifications_total=notifs_total,
                )
                break
        except Exception:
            # Never fail health probe if aggregate telemetry query is unavailable in mock tests
            exec_stats = None
            activity_overview = None

    execution_available = judge0_ok or piston_ok
    overall_ok = db_ok and execution_available
    return AdminOperationsHealthResponse(
        overall_status="ok" if overall_ok else "degraded",
        environment=settings.app_env,
        rate_limit_enabled=settings.rate_limit_enabled,
        llm_provider_mode=llm_mode,
        llm_provider=settings.llm_provider,
        llm_model=llm_model_label,
        checks=checks,
        execution_stats=exec_stats,
        activity_overview=activity_overview,
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
