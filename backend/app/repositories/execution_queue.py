"""Async SQLAlchemy repository for transactional outbound execution queue."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import status
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.execution_queue import ExecutionJob, ExecutionWorker
from app.models.problems import ExecutionResult, Submission
from app.schemas.execution_queue import WorkerTestCaseOutcomeInput
from app.schemas.problems import Verdict

_VERDICT_PRIORITY: dict[str, int] = {
    "compilation_error": 6,
    "runtime_error": 5,
    "time_limit_exceeded": 4,
    "memory_limit_exceeded": 3,
    "internal_error": 2,
    "wrong_answer": 1,
    "accepted": 0,
}


def _aggregate_verdict(verdicts: list[Verdict]) -> Verdict:
    if not verdicts:
        return "internal_error"
    return max(verdicts, key=lambda v: _VERDICT_PRIORITY.get(v, 0))


class ExecutionQueueRepository:
    """Transactional persistence for outbound execution workers and queued jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_worker_heartbeat(
        self,
        *,
        worker_id: str,
        display_name: str,
        judge0_version: str | None,
        supported_languages: list[str],
        active_job_count: int | None = None,
        last_error: str | None = None,
    ) -> ExecutionWorker:
        now = datetime.now(UTC)
        update_values: dict[str, Any] = {
            "display_name": display_name,
            "status": "online",
            "judge0_version": judge0_version,
            "supported_languages": supported_languages,
            "last_heartbeat_at": now,
            "last_error": last_error,
            "updated_at": now,
        }
        if active_job_count is not None:
            update_values["active_job_count"] = active_job_count

        stmt = (
            pg_insert(ExecutionWorker)
            .values(
                worker_id=worker_id,
                display_name=display_name,
                status="online",
                judge0_version=judge0_version,
                supported_languages=supported_languages,
                active_job_count=active_job_count or 0,
                last_heartbeat_at=now,
                last_error=last_error,
            )
            .on_conflict_do_update(
                index_elements=[ExecutionWorker.worker_id],
                set_=update_values,
            )
            .returning(ExecutionWorker)
        )
        worker = (await self._session.execute(stmt)).scalar_one()
        await self._session.commit()
        return worker

    async def mark_worker_offline(self, *, worker_id: str, reason: str) -> None:
        now = datetime.now(UTC)
        stmt = (
            update(ExecutionWorker)
            .where(ExecutionWorker.worker_id == worker_id)
            .values(
                status="offline",
                active_job_count=0,
                last_error=reason[:500] if reason else None,
                updated_at=now,
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def get_online_workers_summary(
        self, *, heartbeat_ttl_seconds: int
    ) -> tuple[int, datetime | None, int]:
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=heartbeat_ttl_seconds)

        workers_stmt = select(
            func.count(ExecutionWorker.worker_id),
            func.max(ExecutionWorker.last_heartbeat_at),
        ).where(
            ExecutionWorker.status == "online",
            ExecutionWorker.last_heartbeat_at >= cutoff,
        )
        w_row = (await self._session.execute(workers_stmt)).one()
        active_workers = int(w_row[0] or 0)
        last_hb: datetime | None = w_row[1]

        queue_stmt = select(func.count(ExecutionJob.id)).where(
            ExecutionJob.status == "queued",
            ExecutionJob.expires_at > now,
        )
        queue_depth = int((await self._session.execute(queue_stmt)).scalar_one() or 0)
        return active_workers, last_hb, queue_depth

    async def count_user_active_jobs(self, *, user_id: UUID) -> int:
        now = datetime.now(UTC)
        stmt = select(func.count(ExecutionJob.id)).where(
            ExecutionJob.requested_by == user_id,
            ExecutionJob.status.in_(("queued", "running")),
            ExecutionJob.expires_at > now,
        )
        return int((await self._session.execute(stmt)).scalar_one() or 0)

    async def find_active_duplicate_submission_id(
        self,
        *,
        user_id: UUID,
        dedup_hash: str,
        window_seconds: int = 60,
    ) -> UUID | None:
        now = datetime.now(UTC)
        since = now - timedelta(seconds=window_seconds)
        stmt = (
            select(ExecutionJob.submission_id)
            .where(
                ExecutionJob.requested_by == user_id,
                ExecutionJob.job_type == "submission",
                ExecutionJob.dedup_hash == dedup_hash,
                ExecutionJob.status.in_(("queued", "running")),
                ExecutionJob.created_at >= since,
                ExecutionJob.expires_at > now,
                ExecutionJob.submission_id.is_not(None),
            )
            .order_by(ExecutionJob.created_at.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def enqueue_job(
        self,
        *,
        job_type: str,
        submission_id: UUID | None,
        requested_by: UUID | None,
        language_slug: str,
        judge0_language_id: int,
        dedup_hash: str | None,
        payload_json: dict[str, Any],
        ttl_seconds: int,
        max_attempts: int = 2,
    ) -> ExecutionJob:
        now = datetime.now(UTC)
        job = ExecutionJob(
            job_type=job_type,
            submission_id=submission_id,
            requested_by=requested_by,
            language_slug=language_slug,
            judge0_language_id=judge0_language_id,
            dedup_hash=dedup_hash,
            status="queued",
            payload_json=payload_json,
            max_attempts=max_attempts,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        self._session.add(job)
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def sweep_expired_and_stale_jobs(self) -> int:
        """Expire overdue jobs and reclaim stale worker leases atomically."""
        now = datetime.now(UTC)
        changed = 0

        # 1. Hard-expired queued or running jobs
        expired_stmt = (
            select(ExecutionJob)
            .where(
                ExecutionJob.status.in_(("queued", "running")),
                ExecutionJob.expires_at <= now,
            )
            .with_for_update(skip_locked=True)
            .limit(50)
        )
        expired_jobs = list((await self._session.execute(expired_stmt)).scalars().all())
        for job in expired_jobs:
            was_running = job.status == "running"
            job.status = "timed_out"
            job.completed_at = now
            job.error_code = "EXECUTION_TIMEOUT"
            job.error_message = (
                "Execution timed out while running on the local Judge0 runner."
                if was_running
                else (
                    "Execution timed out in the queue because the local Judge0 runner "
                    "did not pick it up in time."
                )
            )
            if job.submission_id is not None:
                await self._fail_submission_if_unfinished(
                    submission_id=job.submission_id,
                    verdict="time_limit_exceeded" if was_running else "internal_error",
                    engine_error="execution_worker_timeout",
                    user_message=job.error_message,
                )
            changed += 1

        # 2. Lease-expired running jobs that have not hit hard expiry yet
        stale_stmt = (
            select(ExecutionJob)
            .where(
                ExecutionJob.status == "running",
                ExecutionJob.lease_expires_at.is_not(None),
                ExecutionJob.lease_expires_at <= now,
                ExecutionJob.expires_at > now,
            )
            .with_for_update(skip_locked=True)
            .limit(50)
        )
        stale_jobs = list((await self._session.execute(stale_stmt)).scalars().all())
        for job in stale_jobs:
            if job.attempt_count < job.max_attempts:
                job.status = "queued"
                job.claimed_by_worker_id = None
                job.claim_token = None
                job.lease_expires_at = None
                job.error_code = "LEASE_EXPIRED_REQUEUED"
                if job.submission_id is not None:
                    await self._session.execute(
                        update(Submission)
                        .where(
                            Submission.id == job.submission_id,
                            Submission.status == "running",
                        )
                        .values(status="queued", updated_at=now)
                    )
            else:
                job.status = "failed"
                job.completed_at = now
                job.error_code = "WORKER_DISCONNECTED"
                job.error_message = (
                    "The local Judge0 runner disconnected before completing execution."
                )
                if job.submission_id is not None:
                    await self._fail_submission_if_unfinished(
                        submission_id=job.submission_id,
                        verdict="internal_error",
                        engine_error="worker_disconnected",
                        user_message=job.error_message,
                    )
            changed += 1

        if changed > 0:
            await self._session.commit()
        return changed

    async def _fail_submission_if_unfinished(
        self,
        *,
        submission_id: UUID,
        verdict: Verdict,
        engine_error: str,
        user_message: str,
    ) -> None:
        sub = (
            await self._session.execute(
                select(Submission).where(Submission.id == submission_id).with_for_update()
            )
        ).scalar_one_or_none()
        if sub is None or sub.status in ("completed", "failed"):
            return
        evidence = dict(sub.execution_evidence or {})
        evidence.update(
            {
                "engine_error": engine_error,
                "user_message": user_message,
            }
        )
        sub.status = "failed"
        sub.verdict = verdict
        sub.execution_evidence = evidence
        sub.updated_at = datetime.now(UTC)

    async def claim_next_job(
        self,
        *,
        worker_id: str,
        lease_seconds: int,
    ) -> ExecutionJob | None:
        now = datetime.now(UTC)
        stmt = (
            select(ExecutionJob)
            .where(
                ExecutionJob.status == "queued",
                ExecutionJob.expires_at > now,
            )
            .order_by(ExecutionJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        job = (await self._session.execute(stmt)).scalar_one_or_none()
        if job is None:
            return None

        job.status = "running"
        job.claimed_by_worker_id = worker_id
        job.claim_token = uuid4()
        job.claimed_at = now
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
        job.attempt_count += 1
        job.updated_at = now

        if job.submission_id is not None:
            await self._session.execute(
                update(Submission)
                .where(
                    Submission.id == job.submission_id,
                    Submission.status == "queued",
                )
                .values(status="running", updated_at=now)
            )

        await self._session.execute(
            update(ExecutionWorker)
            .where(ExecutionWorker.worker_id == worker_id)
            .values(
                active_job_count=ExecutionWorker.active_job_count + 1,
                last_heartbeat_at=now,
                updated_at=now,
            )
        )
        await self._session.commit()
        await self._session.refresh(job)
        return job

    async def complete_job(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        claim_token: UUID,
        outcomes: list[WorkerTestCaseOutcomeInput],
        engine_error: str | None,
        error_code: str | None,
    ) -> tuple[ExecutionJob, Verdict | None]:
        now = datetime.now(UTC)
        job = (
            await self._session.execute(
                select(ExecutionJob).where(ExecutionJob.id == job_id).with_for_update()
            )
        ).scalar_one_or_none()
        if job is None:
            raise AppError(
                code="JOB_NOT_FOUND",
                message="Execution job was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if (
            job.status != "running"
            or job.claimed_by_worker_id != worker_id
            or job.claim_token != claim_token
        ):
            raise AppError(
                code="JOB_CLAIM_MISMATCH",
                message="Execution job is no longer leased to this worker token.",
                status_code=status.HTTP_409_CONFLICT,
            )

        overall_verdict: Verdict | None = None
        if engine_error:
            job.status = "failed"
            job.error_code = error_code or "EXECUTION_ENGINE_ERROR"
            job.error_message = engine_error[:500]
            job.completed_at = now
            job.result_json = {"engine_error": engine_error[:500]}
            overall_verdict = "internal_error"
            if job.submission_id is not None:
                await self._fail_submission_if_unfinished(
                    submission_id=job.submission_id,
                    verdict="internal_error",
                    engine_error=job.error_code.lower(),
                    user_message=(
                        "The local Judge0 sandbox could not complete this run. "
                        "Please verify Docker Judge0 is healthy and try again."
                    ),
                )
            await self._session.execute(
                update(ExecutionWorker)
                .where(ExecutionWorker.worker_id == worker_id)
                .values(
                    active_job_count=func.greatest(ExecutionWorker.active_job_count - 1, 0),
                    total_jobs_failed=ExecutionWorker.total_jobs_failed + 1,
                    last_error=engine_error[:500],
                    last_heartbeat_at=now,
                    updated_at=now,
                )
            )
            await self._session.commit()
            return job, overall_verdict

        serialized_outcomes = [o.model_dump(mode="json") for o in outcomes]
        job.status = "completed"
        job.completed_at = now
        job.result_json = {"outcomes": serialized_outcomes}
        job.error_code = None
        job.error_message = None

        if job.job_type == "submission" and job.submission_id is not None:
            sub = (
                await self._session.execute(
                    select(Submission).where(Submission.id == job.submission_id).with_for_update()
                )
            ).scalar_one_or_none()
            if sub is not None and sub.status not in ("completed", "failed"):
                verdicts: list[Verdict] = []
                passed_count = 0
                public_passed = 0
                public_total = 0
                hidden_passed = 0
                hidden_total = 0
                max_runtime_ms: int | None = None
                max_memory_kb: int | None = None
                first_failing_public_ordinal: int | None = None
                observed_stderr_snippet: str | None = None
                observed_compile_snippet: str | None = None

                # Build allowed test_case_id lookup from job payload to prevent spoofed IDs
                payload_tcs = job.payload_json.get("test_cases") or []
                allowed_tc_ids: dict[int, tuple[UUID | None, bool]] = {}
                for ptc in payload_tcs:
                    ord_val = int(ptc.get("ordinal", 0))
                    raw_id = ptc.get("test_case_id")
                    allowed_tc_ids[ord_val] = (
                        UUID(str(raw_id)) if raw_id else None,
                        bool(ptc.get("is_hidden", False)),
                    )

                for out in outcomes:
                    verdicts.append(out.verdict)
                    tc_id, tc_hidden = allowed_tc_ids.get(
                        out.ordinal, (out.test_case_id, out.is_hidden)
                    )
                    if tc_hidden:
                        hidden_total += 1
                        if out.verdict == "accepted":
                            hidden_passed += 1
                    else:
                        public_total += 1
                        if out.verdict == "accepted":
                            public_passed += 1
                        elif first_failing_public_ordinal is None:
                            first_failing_public_ordinal = out.ordinal

                    if out.verdict == "accepted":
                        passed_count += 1
                    if out.runtime_ms is not None:
                        max_runtime_ms = (
                            out.runtime_ms
                            if max_runtime_ms is None
                            else max(max_runtime_ms, out.runtime_ms)
                        )
                    if out.memory_kb is not None:
                        max_memory_kb = (
                            out.memory_kb
                            if max_memory_kb is None
                            else max(max_memory_kb, out.memory_kb)
                        )
                    if not tc_hidden and out.stderr and observed_stderr_snippet is None:
                        observed_stderr_snippet = out.stderr[:500]
                    if out.compile_output and observed_compile_snippet is None:
                        observed_compile_snippet = out.compile_output[:500]

                    if tc_id is not None:
                        self._session.add(
                            ExecutionResult(
                                submission_id=sub.id,
                                test_case_id=tc_id,
                                is_hidden=tc_hidden,
                                execution_provider="judge0",
                                judge0_token=out.token,
                                judge0_status_id=out.status_id,
                                verdict=out.verdict,
                                stdout=out.stdout,
                                stderr=out.stderr,
                                compile_output=out.compile_output,
                                runtime_ms=out.runtime_ms,
                                memory_kb=out.memory_kb,
                            )
                        )

                overall_verdict = _aggregate_verdict(verdicts)
                meta = job.payload_json.get("meta") or {}
                evidence: dict[str, Any] = {
                    "mode": meta.get("mode", "coding"),
                    "submission_kind": sub.submission_kind,
                    "language_slug": sub.language_slug,
                    "execution_provider": "judge0",
                    "execution_transport": "outbound_local_worker",
                    "fallback_used": False,
                    "overall_verdict": overall_verdict,
                    "public_passed": public_passed,
                    "public_total": public_total,
                    "hidden_passed": hidden_passed,
                    "hidden_total": hidden_total,
                    "first_failing_public_ordinal": first_failing_public_ordinal,
                    "has_compile_error": overall_verdict == "compilation_error",
                    "has_runtime_error": overall_verdict == "runtime_error",
                    "has_prediction": bool(sub.prediction_text and sub.prediction_text.strip()),
                    "has_explanation": bool(sub.explanation_text and sub.explanation_text.strip()),
                    "stderr_preview": observed_stderr_snippet,
                    "compile_output_preview": observed_compile_snippet,
                    "ai_diagnosis_ready_for_phase_4": True,
                }
                sub.status = "completed"
                sub.verdict = overall_verdict
                sub.passed_tests = passed_count
                sub.total_tests = len(outcomes) if outcomes else sub.total_tests
                sub.runtime_ms = max_runtime_ms
                sub.memory_kb = max_memory_kb
                sub.execution_provider = "judge0"
                sub.execution_evidence = evidence
                sub.updated_at = now
        elif outcomes:
            overall_verdict = _aggregate_verdict([o.verdict for o in outcomes])

        await self._session.execute(
            update(ExecutionWorker)
            .where(ExecutionWorker.worker_id == worker_id)
            .values(
                active_job_count=func.greatest(ExecutionWorker.active_job_count - 1, 0),
                total_jobs_completed=ExecutionWorker.total_jobs_completed + 1,
                last_heartbeat_at=now,
                updated_at=now,
            )
        )
        await self._session.commit()
        return job, overall_verdict

    async def release_job(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        claim_token: UUID,
        reason: str,
        requeue: bool,
    ) -> ExecutionJob:
        now = datetime.now(UTC)
        job = (
            await self._session.execute(
                select(ExecutionJob).where(ExecutionJob.id == job_id).with_for_update()
            )
        ).scalar_one_or_none()
        if job is None:
            raise AppError(
                code="JOB_NOT_FOUND",
                message="Execution job was not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if (
            job.status != "running"
            or job.claimed_by_worker_id != worker_id
            or job.claim_token != claim_token
        ):
            raise AppError(
                code="JOB_CLAIM_MISMATCH",
                message="Execution job is no longer leased to this worker token.",
                status_code=status.HTTP_409_CONFLICT,
            )

        if requeue and job.attempt_count < job.max_attempts and job.expires_at > now:
            job.status = "queued"
            job.claimed_by_worker_id = None
            job.claim_token = None
            job.lease_expires_at = None
            job.error_code = "WORKER_RELEASED_REQUEUED"
            job.error_message = reason[:200]
            if job.submission_id is not None:
                await self._session.execute(
                    update(Submission)
                    .where(Submission.id == job.submission_id, Submission.status == "running")
                    .values(status="queued", updated_at=now)
                )
        else:
            job.status = "failed"
            job.completed_at = now
            job.error_code = "WORKER_STOPPED"
            job.error_message = reason[:200]
            if job.submission_id is not None:
                await self._fail_submission_if_unfinished(
                    submission_id=job.submission_id,
                    verdict="internal_error",
                    engine_error="worker_stopped",
                    user_message="The local Judge0 runner stopped before finishing execution.",
                )

        await self._session.execute(
            update(ExecutionWorker)
            .where(ExecutionWorker.worker_id == worker_id)
            .values(
                active_job_count=func.greatest(ExecutionWorker.active_job_count - 1, 0),
                updated_at=now,
            )
        )
        await self._session.commit()
        return job

    async def get_job_by_id(self, job_id: UUID) -> ExecutionJob | None:
        stmt = (
            select(ExecutionJob)
            .where(ExecutionJob.id == job_id)
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_job_for_submission(self, submission_id: UUID) -> ExecutionJob | None:
        stmt = (
            select(ExecutionJob)
            .where(ExecutionJob.submission_id == submission_id)
            .order_by(ExecutionJob.created_at.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def cancel_submission_job(self, *, submission_id: UUID, user_id: UUID) -> bool:
        now = datetime.now(UTC)
        job = (
            await self._session.execute(
                select(ExecutionJob)
                .where(
                    ExecutionJob.submission_id == submission_id,
                    ExecutionJob.requested_by == user_id,
                    ExecutionJob.status == "queued",
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if job is None:
            return False
        job.status = "cancelled"
        job.completed_at = now
        job.error_code = "CANCELLED_BY_USER"
        job.error_message = "Execution was cancelled before starting."
        await self._fail_submission_if_unfinished(
            submission_id=submission_id,
            verdict="internal_error",
            engine_error="cancelled_by_user",
            user_message="Execution was cancelled before starting.",
        )
        await self._session.commit()
        return True
