"""Bounded in-process execution queue consumer orchestrated inside FastAPI lifespan.

Security & Free-Tier Invariants:
- NEVER executes arbitrary student code inside FastAPI. Always delegates execution
  over HTTPS to an isolated Judge0 CE sandbox (with optional verified Piston fallback).
- Refuses loopback or non-HTTPS upstream execution URLs in production.
- Enforces a single process-wide consumer guard so duplicate consumers cannot start.
- Uses durable PostgreSQL-backed state (`execution_workers`, `execution_jobs`),
  atomic `FOR UPDATE SKIP LOCKED` job claiming, periodic heartbeat & lease renewal,
  bounded concurrency, abandoned-job recovery, retry caps, and graceful shutdown.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import socket
import threading
import time
import uuid
from urllib.parse import ParseResult, urlparse
from uuid import UUID

import httpx

from app.core.config import Settings
from app.core.database import DatabaseManager, get_db_manager
from app.core.errors import AppError
from app.core.logging import get_logger
from app.integrations.execution.router import ResilientExecutionClient
from app.integrations.judge0.client import (
    HttpJudge0Client,
    Judge0Client,
    build_judge0_auth_headers,
)
from app.integrations.piston.client import HttpPistonClient, is_piston_configured
from app.models.execution_queue import ExecutionJob
from app.repositories.execution_queue import ExecutionQueueRepository
from app.schemas.execution_queue import WorkerTestCaseOutcomeInput
from app.services.execution.queue_hub import ExecutionQueueHub, get_execution_queue_hub
from app.services.execution.worker_service import is_worker_queue_mode

logger = get_logger(__name__)

SUPPORTED_LANGUAGES: list[str] = ["python", "javascript", "c", "cpp", "java"]
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

_REGISTRY_LOCK = threading.Lock()
_ACTIVE_WORKER: EmbeddedExecutionWorker | None = None


_TRANSIENT_ENGINE_ERROR_CODES = frozenset(
    {
        "EXECUTION_SERVICE_UNAVAILABLE",
        "SANDBOX_EXECUTION_ERROR",
        "JUDGE0_UNAVAILABLE",
        "PISTON_UNAVAILABLE",
    }
)


def _safe_urlparse(url: str) -> ParseResult | None:
    try:
        return urlparse(url)
    except ValueError:
        return None


def _is_loopback_url(url: str) -> bool:
    parsed = _safe_urlparse(url)
    if parsed is None:
        return False
    host = (parsed.hostname or "").strip().lower()
    return host in _LOOPBACK_HOSTS


def resolve_embedded_upstream_settings(settings: Settings) -> Settings | None:
    """Resolve isolated upstream Judge0 settings for the embedded lifespan consumer.

    Returns None when no safe upstream Judge0 URL is configured.
    """
    primary_url = (settings.judge0_base_url or "").strip()
    embedded_url = (settings.execution_embedded_judge0_base_url or "").strip()

    chosen_url = ""
    from_primary = False
    if primary_url:
        parsed_primary = _safe_urlparse(primary_url)
        if parsed_primary is None:
            logger.warning("embedded_worker_invalid_primary_url")
        elif not _is_loopback_url(primary_url):
            chosen_url = primary_url
            from_primary = True
    if not chosen_url and embedded_url:
        chosen_url = embedded_url

    if not chosen_url:
        return None

    parsed = _safe_urlparse(chosen_url)
    if parsed is None or parsed.scheme not in ("https", "http") or not parsed.netloc:
        logger.warning("embedded_worker_invalid_upstream_url")
        return None

    chosen_host = (parsed.hostname or "").strip().lower()
    is_rapidapi_host = chosen_host == "rapidapi.com" or chosen_host.endswith(".rapidapi.com")
    is_public_ce_host = chosen_host == "ce.judge0.com"

    # Never forward RapidAPI keys to non-RapidAPI hosts, and never forward local
    # self-hosted auth tokens to the public ce.judge0.com fallback endpoint.
    effective_rapidapi_key = (
        (settings.judge0_rapidapi_key or "").strip() if is_rapidapi_host else ""
    )
    effective_rapidapi_host = (
        (settings.judge0_rapidapi_host or "").strip() if is_rapidapi_host else ""
    )
    effective_auth_token = (
        (settings.judge0_auth_token or "").strip()
        if (not is_rapidapi_host and (from_primary or not is_public_ce_host))
        else ""
    )

    has_credential = bool(effective_auth_token or effective_rapidapi_key)
    if parsed.scheme != "https" and has_credential and not _is_loopback_url(chosen_url):
        logger.warning(
            "embedded_worker_blocked_plaintext_credential_url",
            scheme=parsed.scheme,
        )
        return None

    if settings.app_env == "production" and (
        parsed.scheme != "https" or _is_loopback_url(chosen_url)
    ):
        logger.warning(
            "embedded_worker_blocked_unsafe_production_url",
            scheme=parsed.scheme,
        )
        return None

    upstream_mode = "rapidapi" if is_rapidapi_host else "auth_token"

    return Settings(
        _env_file=None,
        app_env=settings.app_env,
        judge0_base_url=chosen_url,
        judge0_auth_mode=upstream_mode,
        judge0_auth_token=effective_auth_token,
        judge0_rapidapi_key=effective_rapidapi_key,
        judge0_rapidapi_host=effective_rapidapi_host,
        judge0_http_timeout_seconds=settings.judge0_http_timeout_seconds,
        judge0_poll_interval_seconds=settings.judge0_poll_interval_seconds,
        judge0_poll_timeout_seconds=settings.judge0_poll_timeout_seconds,
        judge0_max_retries=settings.judge0_max_retries,
        execution_fallback_enabled=settings.execution_fallback_enabled,
        piston_enabled=settings.piston_enabled,
        piston_base_url=settings.piston_base_url,
        piston_isolated_host_verified=settings.piston_isolated_host_verified,
        piston_http_timeout_seconds=settings.piston_http_timeout_seconds,
        piston_compile_timeout_ms=settings.piston_compile_timeout_ms,
        piston_run_timeout_ms=settings.piston_run_timeout_ms,
        piston_max_output_bytes=settings.piston_max_output_bytes,
    )


def _default_worker_id() -> str:
    host = "".join(ch for ch in socket.gethostname().lower() if ch.isalnum() or ch in "-_")[:18]
    short = uuid.uuid4().hex[:6]
    return f"web-{host or 'api'}-{os.getpid()}-{short}"[:64]


class EmbeddedExecutionWorker:
    """Bounded async consumer that executes queued jobs via isolated remote Judge0 CE."""

    def __init__(
        self,
        *,
        settings: Settings,
        db_manager: DatabaseManager | None = None,
        hub: ExecutionQueueHub | None = None,
        executor: Judge0Client | None = None,
        upstream_settings: Settings | None = None,
        worker_id: str | None = None,
        display_name: str | None = None,
    ) -> None:
        self._settings = settings
        self._db_manager = db_manager
        self._hub = hub or get_execution_queue_hub()
        self._upstream_settings = upstream_settings or resolve_embedded_upstream_settings(settings)
        self._worker_id = (worker_id or _default_worker_id())[:64]
        self._display_name = display_name or "Embedded Isolated Judge0 Consumer"
        self._concurrency = max(1, min(settings.execution_embedded_worker_concurrency, 2))
        self._poll_seconds = max(1.0, min(settings.execution_embedded_worker_poll_seconds, 30.0))
        self._heartbeat_seconds = max(
            5.0,
            min(
                settings.execution_embedded_worker_heartbeat_seconds,
                max(5.0, float(settings.execution_worker_heartbeat_ttl_seconds) * 0.6),
            ),
        )
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._inflight_tasks: set[asyncio.Task[None]] = set()
        self._semaphore = asyncio.Semaphore(self._concurrency)
        self._judge0_version: str | None = None
        self._upstream_healthy: bool = executor is not None
        self._last_probe_monotonic: float = 0.0
        self._last_heartbeat_monotonic: float = 0.0

        if executor is not None:
            self._executor: Judge0Client | None = executor
        elif self._upstream_settings is not None:
            primary = HttpJudge0Client(self._upstream_settings)
            fallback = (
                HttpPistonClient(self._upstream_settings)
                if is_piston_configured(self._upstream_settings)
                else None
            )
            self._executor = ResilientExecutionClient(
                primary=primary,
                fallback=fallback,
                settings=self._upstream_settings,
            )
        else:
            self._executor = None

    @property
    def worker_id(self) -> str:
        return self._worker_id

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def _manager(self) -> DatabaseManager:
        return self._db_manager or get_db_manager()

    async def probe_upstream(self) -> tuple[bool, str | None]:
        """Verify isolated upstream Judge0 (or verified Piston fallback) before heartbeating."""
        if self._executor is None:
            return False, None
        if self._upstream_settings is None:
            # Custom injected executor (e.g., unit tests)
            self._upstream_healthy = True
            self._judge0_version = self._judge0_version or "injected"
            self._last_probe_monotonic = time.monotonic()
            return True, self._judge0_version

        j0_url = self._upstream_settings.judge0_base_url.rstrip("/")
        try:
            headers = build_judge0_auth_headers(self._upstream_settings)
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{j0_url}/about", headers=headers)
                if resp.status_code == 200:
                    version = str(resp.json().get("version", "1.14.0"))
                    self._judge0_version = version
                    self._upstream_healthy = True
                    self._last_probe_monotonic = time.monotonic()
                    return True, version
        except Exception as exc:
            logger.warning(
                "embedded_worker_judge0_probe_failed",
                worker_id=self._worker_id,
                error_type=type(exc).__name__,
            )

        if is_piston_configured(self._upstream_settings):
            piston_url = self._upstream_settings.piston_base_url.rstrip("/")
            try:
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(f"{piston_url}/api/v2/runtimes")
                    if resp.status_code == 200 and isinstance(resp.json(), list) and resp.json():
                        self._judge0_version = "piston-fallback"
                        self._upstream_healthy = True
                        self._last_probe_monotonic = time.monotonic()
                        return True, self._judge0_version
            except Exception as exc:
                logger.warning(
                    "embedded_worker_piston_probe_failed",
                    worker_id=self._worker_id,
                    error_type=type(exc).__name__,
                )

        self._upstream_healthy = False
        self._last_probe_monotonic = time.monotonic()
        return False, None

    async def _send_heartbeat(self, *, active_job_count: int | None = None) -> None:
        async for session in self._manager().session():
            repo = ExecutionQueueRepository(session)
            await repo.upsert_worker_heartbeat(
                worker_id=self._worker_id,
                display_name=self._display_name,
                judge0_version=self._judge0_version,
                supported_languages=SUPPORTED_LANGUAGES,
                active_job_count=active_job_count,
            )
            self._last_heartbeat_monotonic = time.monotonic()
            break

    async def _mark_offline(self, reason: str) -> None:
        try:
            async for session in self._manager().session():
                repo = ExecutionQueueRepository(session)
                await repo.mark_worker_offline(worker_id=self._worker_id, reason=reason)
                break
        except Exception as exc:
            logger.warning(
                "embedded_worker_mark_offline_failed",
                worker_id=self._worker_id,
                error_type=type(exc).__name__,
            )

    async def _sweep_and_claim(self) -> ExecutionJob | None:
        async for session in self._manager().session():
            repo = ExecutionQueueRepository(session)
            await repo.sweep_expired_and_stale_jobs()
            now_mono = time.monotonic()
            if (now_mono - self._last_heartbeat_monotonic) >= self._heartbeat_seconds:
                await repo.upsert_worker_heartbeat(
                    worker_id=self._worker_id,
                    display_name=self._display_name,
                    judge0_version=self._judge0_version,
                    supported_languages=SUPPORTED_LANGUAGES,
                )
                self._last_heartbeat_monotonic = now_mono
            job = await repo.claim_next_job(
                worker_id=self._worker_id,
                lease_seconds=self._settings.execution_job_lease_seconds,
            )
            return job
        return None

    async def _lease_keeper(
        self,
        *,
        job_id: UUID,
        claim_token: UUID,
        done_event: asyncio.Event,
    ) -> None:
        interval = max(5.0, min(self._heartbeat_seconds, 15.0))
        while not done_event.is_set() and not self._stop_event.is_set():
            try:
                await asyncio.wait_for(done_event.wait(), timeout=interval)
                return
            except TimeoutError:
                pass
            try:
                async for session in self._manager().session():
                    repo = ExecutionQueueRepository(session)
                    renewed, _ = await repo.renew_job_lease(
                        job_id=job_id,
                        worker_id=self._worker_id,
                        claim_token=claim_token,
                        lease_seconds=self._settings.execution_job_lease_seconds,
                    )
                    if renewed:
                        self._last_heartbeat_monotonic = time.monotonic()
                    else:
                        return
                    break
            except Exception as exc:
                logger.warning(
                    "embedded_worker_lease_renew_failed",
                    worker_id=self._worker_id,
                    job_id=str(job_id),
                    error_type=type(exc).__name__,
                )

    async def _release_job(self, *, job_id: UUID, claim_token: UUID, reason: str) -> None:
        try:
            async for session in self._manager().session():
                repo = ExecutionQueueRepository(session)
                job = await repo.release_job(
                    job_id=job_id,
                    worker_id=self._worker_id,
                    claim_token=claim_token,
                    reason=reason,
                    requeue=True,
                )
                if job.status == "queued":
                    self._hub.notify_new_job()
                else:
                    self._hub.notify_job_done(job.id)
                break
        except Exception as exc:
            logger.warning(
                "embedded_worker_release_failed",
                worker_id=self._worker_id,
                job_id=str(job_id),
                error_type=type(exc).__name__,
            )

    async def execute_claimed_job(self, job: ExecutionJob) -> None:
        """Execute a single claimed job against the isolated sandbox and persist results."""
        assert self._executor is not None
        assert job.claim_token is not None

        job_id = job.id
        claim_token = job.claim_token
        payload = job.payload_json or {}
        source_code = str(payload.get("source_code", ""))
        cpu_limit = float(payload.get("cpu_time_limit_seconds", 2.0))
        mem_limit = int(payload.get("memory_limit_kb", 131072))
        test_cases = list(payload.get("test_cases") or [])

        logger.info(
            "embedded_worker_executing_job",
            worker_id=self._worker_id,
            job_id=str(job_id),
            language_slug=job.language_slug,
            test_count=len(test_cases),
        )

        done_event = asyncio.Event()
        keeper_task = asyncio.create_task(
            self._lease_keeper(job_id=job_id, claim_token=claim_token, done_event=done_event)
        )

        outcomes: list[WorkerTestCaseOutcomeInput] = []
        engine_error: str | None = None
        error_code: str | None = None

        try:
            for tc in test_cases:
                res = await self._executor.execute_test_case(
                    source_code=source_code,
                    judge0_language_id=job.judge0_language_id,
                    stdin=str(tc.get("stdin", "")),
                    expected_output=str(tc.get("expected_output", "")),
                    cpu_time_limit_seconds=cpu_limit,
                    memory_limit_kb=mem_limit,
                )
                raw_tc_id = tc.get("test_case_id")
                parsed_tc_id = UUID(str(raw_tc_id)) if raw_tc_id else None
                outcomes.append(
                    WorkerTestCaseOutcomeInput(
                        test_case_id=parsed_tc_id,
                        ordinal=int(tc.get("ordinal", 1)),
                        is_hidden=bool(tc.get("is_hidden", False)),
                        token=res.token,
                        status_id=res.status_id,
                        status_description=res.status_description,
                        verdict=res.verdict,
                        stdout=res.stdout[:131072] if res.stdout is not None else None,
                        stderr=res.stderr[:131072] if res.stderr is not None else None,
                        compile_output=(
                            res.compile_output[:131072] if res.compile_output is not None else None
                        ),
                        runtime_ms=res.runtime_ms,
                        memory_kb=res.memory_kb,
                        execution_provider=res.execution_provider,
                    )
                )
                # Fast-fail remaining test cases on compilation error
                if res.verdict == "compilation_error":
                    for rem in test_cases[len(outcomes) :]:
                        rem_raw_id = rem.get("test_case_id")
                        outcomes.append(
                            WorkerTestCaseOutcomeInput(
                                test_case_id=UUID(str(rem_raw_id)) if rem_raw_id else None,
                                ordinal=int(rem.get("ordinal", 1)),
                                is_hidden=bool(rem.get("is_hidden", False)),
                                token=res.token,
                                status_id=res.status_id,
                                status_description=res.status_description,
                                verdict="compilation_error",
                                stdout=None,
                                stderr=None,
                                compile_output=(
                                    res.compile_output[:131072]
                                    if res.compile_output is not None
                                    else None
                                ),
                                runtime_ms=None,
                                memory_kb=None,
                                execution_provider=res.execution_provider,
                            )
                        )
                    break
        except asyncio.CancelledError:
            done_event.set()
            keeper_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await keeper_task
            await self._release_job(
                job_id=job_id, claim_token=claim_token, reason="embedded_worker_shutdown"
            )
            raise
        except AppError as exc:
            engine_error = exc.message
            error_code = exc.code
            logger.error(
                "embedded_worker_sandbox_error",
                worker_id=self._worker_id,
                job_id=str(job_id),
                code=exc.code,
            )
        except Exception as exc:
            engine_error = f"Isolated sandbox execution failed ({type(exc).__name__})."
            error_code = "SANDBOX_EXECUTION_ERROR"
            logger.error(
                "embedded_worker_unexpected_error",
                worker_id=self._worker_id,
                job_id=str(job_id),
                error_type=type(exc).__name__,
            )
        finally:
            done_event.set()
            keeper_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await keeper_task

        if (
            engine_error
            and (error_code or "") in _TRANSIENT_ENGINE_ERROR_CODES
            and job.attempt_count < job.max_attempts
        ):
            logger.warning(
                "embedded_worker_requeuing_transient_error",
                worker_id=self._worker_id,
                job_id=str(job_id),
                attempt=job.attempt_count,
                max_attempts=job.max_attempts,
                error_code=error_code,
            )
            await self._release_job(
                job_id=job_id,
                claim_token=claim_token,
                reason=f"transient_{(error_code or 'error').lower()}",
            )
            return

        try:
            async for session in self._manager().session():
                repo = ExecutionQueueRepository(session)
                completed_job, overall_verdict = await repo.complete_job(
                    job_id=job_id,
                    worker_id=self._worker_id,
                    claim_token=claim_token,
                    outcomes=outcomes,
                    engine_error=engine_error,
                    error_code=error_code,
                    transport="embedded_lifespan_worker",
                )
                self._hub.notify_job_done(completed_job.id)
                logger.info(
                    "embedded_worker_job_completed",
                    worker_id=self._worker_id,
                    job_id=str(completed_job.id),
                    status=completed_job.status,
                    verdict=overall_verdict,
                )
                break
        except AppError as exc:
            if exc.status_code == 409:
                logger.warning(
                    "embedded_worker_claim_expired",
                    worker_id=self._worker_id,
                    job_id=str(job_id),
                )
                return
            logger.error(
                "embedded_worker_complete_failed",
                worker_id=self._worker_id,
                job_id=str(job_id),
                code=exc.code,
            )

    async def process_one_cycle(self) -> bool:
        """Execute one sweep/heartbeat/claim cycle; returns True if a job was executed."""
        if not self._upstream_healthy or (time.monotonic() - self._last_probe_monotonic) >= 60.0:
            ok, _ = await self.probe_upstream()
            if not ok:
                await self._mark_offline("upstream_sandbox_unreachable")
                return False

        job = await self._sweep_and_claim()
        if job is None:
            return False

        async with self._semaphore:
            await self.execute_claimed_job(job)
        return True

    async def _wait_for_wakeup_or_stop(self, timeout_seconds: float) -> None:
        stop_wait = asyncio.create_task(self._stop_event.wait())
        job_wait = asyncio.create_task(self._hub.wait_for_new_job(timeout_seconds))
        try:
            _, pending = await asyncio.wait(
                {stop_wait, job_wait},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for p in pending:
                p.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await p
        except asyncio.CancelledError:
            stop_wait.cancel()
            job_wait.cancel()
            raise

    async def _run_loop(self) -> None:
        error_backoff = 3.0
        registered = False
        try:
            while not self._stop_event.is_set():
                try:
                    if not registered:
                        ok, version = await self.probe_upstream()
                        if not ok:
                            logger.warning(
                                "embedded_worker_upstream_unavailable_on_boot",
                                worker_id=self._worker_id,
                            )
                            await self._wait_for_wakeup_or_stop(min(30.0, 10.0))
                            continue
                        await self._send_heartbeat(active_job_count=0)
                        registered = True
                        error_backoff = 3.0
                        logger.info(
                            "embedded_worker_started",
                            worker_id=self._worker_id,
                            judge0_version=version,
                            concurrency=self._concurrency,
                        )

                    processed = await self.process_one_cycle()
                    error_backoff = 3.0
                    if processed:
                        continue
                    wait_for = self._poll_seconds if self._upstream_healthy else min(30.0, 10.0)
                    await self._wait_for_wakeup_or_stop(wait_for)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning(
                        "embedded_worker_cycle_error",
                        worker_id=self._worker_id,
                        registered=registered,
                        error_type=type(exc).__name__,
                        backoff_seconds=error_backoff,
                    )
                    await self._wait_for_wakeup_or_stop(error_backoff)
                    error_backoff = min(error_backoff * 1.5, 30.0)
        finally:
            await self._mark_offline("graceful_shutdown")
            logger.info("embedded_worker_stopped", worker_id=self._worker_id)

    def start(self) -> None:
        if self._executor is None:
            logger.warning("embedded_worker_not_started_no_upstream")
            return
        if self.is_running:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(
            self._run_loop(),
            name=f"embedded-worker-{self._worker_id}",
        )

    async def stop(self) -> None:
        self._stop_event.set()
        self._hub.notify_new_job()
        task = self._task
        if task is None:
            return
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=10.0)
        except TimeoutError:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None


def start_embedded_worker_if_enabled(
    *,
    settings: Settings,
    db_manager: DatabaseManager | None = None,
    hub: ExecutionQueueHub | None = None,
) -> EmbeddedExecutionWorker | None:
    """Start at most one embedded worker consumer per process when enabled."""
    global _ACTIVE_WORKER

    if not is_worker_queue_mode(settings) or not settings.execution_embedded_worker_enabled:
        return None

    upstream = resolve_embedded_upstream_settings(settings)
    if upstream is None:
        return None

    with _REGISTRY_LOCK:
        if _ACTIVE_WORKER is not None and _ACTIVE_WORKER.is_running:
            logger.info(
                "embedded_worker_duplicate_start_prevented",
                worker_id=_ACTIVE_WORKER.worker_id,
            )
            return _ACTIVE_WORKER
        worker = EmbeddedExecutionWorker(
            settings=settings,
            db_manager=db_manager,
            hub=hub,
            upstream_settings=upstream,
        )
        worker.start()
        _ACTIVE_WORKER = worker
        return worker


async def stop_embedded_worker(worker: EmbeddedExecutionWorker | None = None) -> None:
    """Stop the active embedded worker consumer gracefully and clear the process guard."""
    global _ACTIVE_WORKER

    target: EmbeddedExecutionWorker | None
    with _REGISTRY_LOCK:
        target = worker or _ACTIVE_WORKER
        if target is _ACTIVE_WORKER:
            _ACTIVE_WORKER = None

    if target is not None:
        await target.stop()


def get_active_embedded_worker() -> EmbeddedExecutionWorker | None:
    """Return the currently registered process-local embedded worker, if any."""
    with _REGISTRY_LOCK:
        return _ACTIVE_WORKER
