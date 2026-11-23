"""Service orchestrating outbound execution worker availability, claiming, and result ingestion."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.config import Settings
from app.integrations.judge0.client import is_judge0_configured
from app.integrations.piston.client import is_piston_configured
from app.repositories.execution_queue import ExecutionQueueRepository
from app.schemas.execution_queue import (
    ExecutionAvailabilityResponse,
    WorkerClaimedJobResponse,
    WorkerClaimRequest,
    WorkerClaimResponse,
    WorkerHeartbeatRequest,
    WorkerHeartbeatResponse,
    WorkerJobReleaseRequest,
    WorkerJobResultRequest,
    WorkerJobResultResponse,
    WorkerJobTestCasePayload,
    WorkerOfflineRequest,
)
from app.services.execution.queue_hub import ExecutionQueueHub, get_execution_queue_hub


def is_worker_queue_mode(settings: Settings) -> bool:
    return (settings.judge0_auth_mode or "auto").strip().lower() == "worker_queue"


class ExecutionWorkerService:
    """Handles outbound worker heartbeats, transactional claiming, and execution observability."""

    def __init__(
        self,
        *,
        repo: ExecutionQueueRepository,
        settings: Settings,
        hub: ExecutionQueueHub | None = None,
    ) -> None:
        self._repo = repo
        self._settings = settings
        self._hub = hub or get_execution_queue_hub()

    async def get_availability(self) -> ExecutionAvailabilityResponse:
        if is_worker_queue_mode(self._settings):
            await self._repo.sweep_expired_and_stale_jobs()
            active_workers, last_hb, queue_depth = await self._repo.get_online_workers_summary(
                heartbeat_ttl_seconds=self._settings.execution_worker_heartbeat_ttl_seconds
            )
            online = active_workers > 0
            return ExecutionAvailabilityResponse(
                mode="worker_queue",
                available=online,
                worker_online=online,
                active_workers=active_workers,
                queue_depth=queue_depth,
                last_heartbeat_at=last_hb,
                message=(
                    "Local Judge0 Code Runner is online and ready for Python, JavaScript, "
                    "C, C++, and Java."
                    if online
                    else (
                        "Code execution is currently unavailable because the local Judge0 runner "
                        "is offline. Start ThinkFirst Code Runner on the host PC to execute code."
                    )
                ),
            )

        if is_judge0_configured(self._settings) or is_piston_configured(self._settings):
            return ExecutionAvailabilityResponse(
                mode="direct_judge0",
                available=True,
                worker_online=True,
                active_workers=1,
                queue_depth=0,
                last_heartbeat_at=datetime.now(UTC),
                message="Direct Judge0 sandbox execution is configured.",
            )

        return ExecutionAvailabilityResponse(
            mode="disabled",
            available=False,
            worker_online=False,
            active_workers=0,
            queue_depth=0,
            last_heartbeat_at=None,
            message=(
                "Live code execution is temporarily unavailable while the sandbox is offline. "
                "You can still read lessons, save revisions, and complete diagnostics."
            ),
        )

    async def heartbeat(
        self, *, worker_id: str, payload: WorkerHeartbeatRequest
    ) -> WorkerHeartbeatResponse:
        await self._repo.sweep_expired_and_stale_jobs()
        worker = await self._repo.upsert_worker_heartbeat(
            worker_id=worker_id,
            display_name=payload.display_name,
            judge0_version=payload.judge0_version,
            supported_languages=payload.supported_languages,
            active_job_count=payload.active_job_count,
            last_error=payload.last_error,
        )
        _, _, queue_depth = await self._repo.get_online_workers_summary(
            heartbeat_ttl_seconds=self._settings.execution_worker_heartbeat_ttl_seconds
        )
        return WorkerHeartbeatResponse(
            worker_id=worker.worker_id,
            status="online",
            queue_depth=queue_depth,
            server_time=datetime.now(UTC),
        )

    async def claim_job(
        self, *, worker_id: str, payload: WorkerClaimRequest
    ) -> WorkerClaimResponse:
        await self._repo.sweep_expired_and_stale_jobs()
        await self._repo.upsert_worker_heartbeat(
            worker_id=worker_id,
            display_name=payload.display_name,
            judge0_version=payload.judge0_version,
            supported_languages=payload.supported_languages,
        )

        job = await self._repo.claim_next_job(
            worker_id=worker_id,
            lease_seconds=self._settings.execution_job_lease_seconds,
        )
        if job is None and payload.wait_seconds > 0:
            woken = await self._hub.wait_for_new_job(float(payload.wait_seconds))
            if woken:
                job = await self._repo.claim_next_job(
                    worker_id=worker_id,
                    lease_seconds=self._settings.execution_job_lease_seconds,
                )

        if job is None:
            return WorkerClaimResponse(job=None, poll_after_seconds=2.0)

        assert job.claim_token is not None
        raw_tcs = job.payload_json.get("test_cases") or []
        tcs = [WorkerJobTestCasePayload.model_validate(item) for item in raw_tcs]
        return WorkerClaimResponse(
            job=WorkerClaimedJobResponse(
                job_id=job.id,
                job_type=job.job_type,
                submission_id=job.submission_id,
                claim_token=job.claim_token,
                language_slug=job.language_slug,
                judge0_language_id=job.judge0_language_id,
                source_code=str(job.payload_json.get("source_code", "")),
                cpu_time_limit_seconds=float(job.payload_json.get("cpu_time_limit_seconds", 2.0)),
                memory_limit_kb=int(job.payload_json.get("memory_limit_kb", 131072)),
                test_cases=tcs,
                expires_at=job.expires_at,
            ),
            poll_after_seconds=0.2,
        )

    async def submit_result(
        self, *, worker_id: str, job_id: UUID, payload: WorkerJobResultRequest
    ) -> WorkerJobResultResponse:
        job, overall_verdict = await self._repo.complete_job(
            job_id=job_id,
            worker_id=worker_id,
            claim_token=payload.claim_token,
            outcomes=payload.outcomes,
            engine_error=payload.engine_error,
            error_code=payload.error_code,
        )
        self._hub.notify_job_done(job.id)
        return WorkerJobResultResponse(
            job_id=job.id,
            status=job.status,
            submission_id=job.submission_id,
            verdict=overall_verdict,
        )

    async def release_job(
        self, *, worker_id: str, job_id: UUID, payload: WorkerJobReleaseRequest
    ) -> WorkerJobResultResponse:
        job = await self._repo.release_job(
            job_id=job_id,
            worker_id=worker_id,
            claim_token=payload.claim_token,
            reason=payload.reason,
            requeue=payload.requeue,
        )
        if job.status == "queued":
            self._hub.notify_new_job()
        else:
            self._hub.notify_job_done(job.id)
        return WorkerJobResultResponse(
            job_id=job.id,
            status=job.status,
            submission_id=job.submission_id,
            verdict=None,
        )

    async def mark_offline(self, *, worker_id: str, payload: WorkerOfflineRequest) -> None:
        await self._repo.mark_worker_offline(worker_id=worker_id, reason=payload.reason)
