"""Judge0Client adapter that routes single test-case executions through the outbound worker queue.

Used transparently by LessonsAndTracksService (guided exercises),
DiagnosticAssessmentService (coding diagnostics), and Admin validation when
JUDGE0_AUTH_MODE=worker_queue.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import status

from app.core.config import Settings
from app.core.database import DatabaseManager, get_db_manager
from app.core.errors import AppError
from app.integrations.judge0.client import (
    Judge0ExecutionOutcome,
    Judge0Language,
)
from app.integrations.piston.client import JUDGE0_ID_TO_SLUG
from app.repositories.execution_queue import ExecutionQueueRepository
from app.services.execution.queue_hub import ExecutionQueueHub, get_execution_queue_hub

_DEFAULT_LANGUAGES: list[Judge0Language] = [
    Judge0Language(id=50, name="C (GCC 9.2.0)"),
    Judge0Language(id=54, name="C++ (GCC 9.2.0)"),
    Judge0Language(id=62, name="Java (OpenJDK 13.0.1)"),
    Judge0Language(id=63, name="JavaScript (Node.js 12.14.0)"),
    Judge0Language(id=71, name="Python (3.8.1)"),
]


class WorkerQueueJudge0Client:
    """Implements Judge0Client protocol via the DB-backed outbound worker queue."""

    def __init__(
        self,
        settings: Settings,
        *,
        db_manager: DatabaseManager | None = None,
        hub: ExecutionQueueHub | None = None,
    ) -> None:
        self._settings = settings
        self._db_manager = db_manager
        self._hub = hub or get_execution_queue_hub()

    def _manager(self) -> DatabaseManager:
        return self._db_manager or get_db_manager()

    async def list_languages(self) -> list[Judge0Language]:
        return list(_DEFAULT_LANGUAGES)

    async def execute_test_case(
        self,
        *,
        source_code: str,
        judge0_language_id: int,
        stdin: str,
        expected_output: str,
        cpu_time_limit_seconds: float,
        memory_limit_kb: int,
    ) -> Judge0ExecutionOutcome:
        language_slug = JUDGE0_ID_TO_SLUG.get(judge0_language_id, "python")

        async for session in self._manager().session():
            repo = ExecutionQueueRepository(session)
            await repo.sweep_expired_and_stale_jobs()
            active_workers, _, queue_depth = await repo.get_online_workers_summary(
                heartbeat_ttl_seconds=self._settings.execution_worker_heartbeat_ttl_seconds
            )
            if active_workers <= 0:
                raise AppError(
                    code="EXECUTION_SERVICE_UNAVAILABLE",
                    message=(
                        "Live code execution is currently unavailable because the local Judge0 "
                        "runner is offline. Start ThinkFirst Code Runner on the host PC "
                        "and try again."
                    ),
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            if queue_depth >= self._settings.execution_max_queue_depth:
                raise AppError(
                    code="EXECUTION_QUEUE_FULL",
                    message=(
                        "Code execution queue is busy right now. Please try again in a few seconds."
                    ),
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            job = await repo.enqueue_job(
                job_type="test_case",
                submission_id=None,
                requested_by=None,
                language_slug=language_slug,
                judge0_language_id=judge0_language_id,
                dedup_hash=None,
                payload_json={
                    "source_code": source_code,
                    "cpu_time_limit_seconds": cpu_time_limit_seconds,
                    "memory_limit_kb": memory_limit_kb,
                    "test_cases": [
                        {
                            "test_case_id": None,
                            "ordinal": 1,
                            "stdin": stdin,
                            "expected_output": expected_output,
                            "is_hidden": False,
                        }
                    ],
                },
                ttl_seconds=self._settings.execution_job_ttl_seconds,
                max_attempts=2,
            )
            job_id = job.id
            break

        self._hub.notify_new_job()

        deadline = (
            asyncio.get_running_loop().time() + self._settings.execution_sync_wait_timeout_seconds
        )
        while asyncio.get_running_loop().time() < deadline:
            remaining = max(0.1, min(1.5, deadline - asyncio.get_running_loop().time()))
            await self._hub.wait_for_job_done(job_id, remaining)
            async for session in self._manager().session():
                repo = ExecutionQueueRepository(session)
                await repo.sweep_expired_and_stale_jobs()
                current = await repo.get_job_by_id(job_id)
                break
            if current is None:
                break
            if current.status == "completed":
                result_json: dict[str, Any] = current.result_json or {}
                outcomes = result_json.get("outcomes") or []
                if outcomes:
                    o = outcomes[0]
                    return Judge0ExecutionOutcome(
                        token=str(o.get("token", "worker-judge0")),
                        status_id=int(o.get("status_id", 13)),
                        status_description=str(o.get("status_description", "Completed")),
                        verdict=o.get("verdict", "internal_error"),
                        stdout=o.get("stdout"),
                        stderr=o.get("stderr"),
                        compile_output=o.get("compile_output"),
                        runtime_ms=o.get("runtime_ms"),
                        memory_kb=o.get("memory_kb"),
                        execution_provider="judge0",
                    )
                break
            if current.status in ("failed", "cancelled", "timed_out"):
                raise AppError(
                    code="EXECUTION_SERVICE_UNAVAILABLE",
                    message=current.error_message
                    or "Local Judge0 runner could not finish execution.",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        raise AppError(
            code="EXECUTION_TIMEOUT",
            message=(
                "Code execution timed out while waiting for the local Judge0 runner. "
                "Check that ThinkFirst Code Runner is running and try again."
            ),
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        )
