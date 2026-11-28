"""Execution availability observability and authenticated outbound worker API routes."""

from __future__ import annotations

import hmac
import re
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response, status

from app.api.v1.deps import (
    get_current_user,
    get_execution_worker_service,
)
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.repositories.identity import UserRecord
from app.schemas.execution_queue import (
    ExecutionAvailabilityResponse,
    WorkerClaimRequest,
    WorkerClaimResponse,
    WorkerHeartbeatRequest,
    WorkerHeartbeatResponse,
    WorkerJobReleaseRequest,
    WorkerJobRenewRequest,
    WorkerJobRenewResponse,
    WorkerJobResultRequest,
    WorkerJobResultResponse,
    WorkerOfflineRequest,
)
from app.services.execution.worker_service import ExecutionWorkerService, is_worker_queue_mode

_WORKER_ID_RE = re.compile(r"^[a-zA-Z0-9._-]{3,64}$")

execution_status_router = APIRouter(prefix="/execution", tags=["Execution & Submissions"])
execution_worker_router = APIRouter(
    prefix="/internal/execution-worker",
    tags=["Internal Execution Worker"],
)


async def require_execution_worker(
    x_worker_token: str | None = Header(default=None, alias="X-Worker-Token"),
    x_worker_id: str | None = Header(default=None, alias="X-Worker-Id"),
    settings: Settings = Depends(get_settings),
) -> str:
    """Authenticate an outbound local execution worker with constant-time token validation."""
    if not is_worker_queue_mode(settings):
        raise AppError(
            code="WORKER_QUEUE_DISABLED",
            message="Execution worker queue mode is not enabled on this server.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    expected_token = (settings.execution_worker_token or "").strip()
    if len(expected_token) < 24:
        raise AppError(
            code="WORKER_QUEUE_MISCONFIGURED",
            message="Execution worker authentication is not configured on this server.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    provided_token = (x_worker_token or "").strip()
    if not provided_token or not hmac.compare_digest(
        provided_token.encode("utf-8"),
        expected_token.encode("utf-8"),
    ):
        raise AppError(
            code="WORKER_AUTH_FAILED",
            message="Invalid or missing execution worker credentials.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    worker_id = (x_worker_id or "").strip()
    if not _WORKER_ID_RE.match(worker_id):
        raise AppError(
            code="INVALID_WORKER_ID",
            message="Missing or malformed X-Worker-Id header.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return worker_id


@execution_status_router.get("/status", response_model=ExecutionAvailabilityResponse)
async def get_execution_status(
    _current_user: UserRecord = Depends(get_current_user),
    service: ExecutionWorkerService = Depends(get_execution_worker_service),
) -> ExecutionAvailabilityResponse:
    """Return non-sensitive live code execution availability for authenticated users."""
    return await service.get_availability()


@execution_worker_router.post("/heartbeat", response_model=WorkerHeartbeatResponse)
async def worker_heartbeat(
    payload: WorkerHeartbeatRequest,
    worker_id: str = Depends(require_execution_worker),
    service: ExecutionWorkerService = Depends(get_execution_worker_service),
) -> WorkerHeartbeatResponse:
    """Register or refresh an authenticated local Judge0 runner's online heartbeat."""
    return await service.heartbeat(worker_id=worker_id, payload=payload)


@execution_worker_router.post("/claim", response_model=WorkerClaimResponse)
async def worker_claim_job(
    payload: WorkerClaimRequest,
    worker_id: str = Depends(require_execution_worker),
    service: ExecutionWorkerService = Depends(get_execution_worker_service),
) -> WorkerClaimResponse:
    """Atomically claim the next approved pending execution job using FOR UPDATE SKIP LOCKED."""
    return await service.claim_job(worker_id=worker_id, payload=payload)


@execution_worker_router.post("/jobs/{job_id}/result", response_model=WorkerJobResultResponse)
async def worker_submit_job_result(
    job_id: UUID,
    payload: WorkerJobResultRequest,
    worker_id: str = Depends(require_execution_worker),
    service: ExecutionWorkerService = Depends(get_execution_worker_service),
) -> WorkerJobResultResponse:
    """Persist verified Judge0 execution outcomes for a leased job."""
    return await service.submit_result(worker_id=worker_id, job_id=job_id, payload=payload)


@execution_worker_router.post("/jobs/{job_id}/release", response_model=WorkerJobResultResponse)
async def worker_release_job(
    job_id: UUID,
    payload: WorkerJobReleaseRequest,
    worker_id: str = Depends(require_execution_worker),
    service: ExecutionWorkerService = Depends(get_execution_worker_service),
) -> WorkerJobResultResponse:
    """Safely release an in-flight leased job during graceful worker shutdown."""
    return await service.release_job(worker_id=worker_id, job_id=job_id, payload=payload)


@execution_worker_router.post("/jobs/{job_id}/renew", response_model=WorkerJobRenewResponse)
async def worker_renew_job_lease(
    job_id: UUID,
    payload: WorkerJobRenewRequest,
    worker_id: str = Depends(require_execution_worker),
    service: ExecutionWorkerService = Depends(get_execution_worker_service),
) -> WorkerJobRenewResponse:
    """Renew an active job lease and worker heartbeat during multi-test execution."""
    return await service.renew_job_lease(worker_id=worker_id, job_id=job_id, payload=payload)


@execution_worker_router.post("/offline", status_code=status.HTTP_204_NO_CONTENT)
async def worker_mark_offline(
    payload: WorkerOfflineRequest,
    worker_id: str = Depends(require_execution_worker),
    service: ExecutionWorkerService = Depends(get_execution_worker_service),
) -> Response:
    """Mark a worker offline on graceful stop so UI shows offline state immediately."""
    await service.mark_offline(worker_id=worker_id, payload=payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
