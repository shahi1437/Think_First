"""ThinkFirst Outbound Local Judge0 Execution Worker.

Connects OUTBOUND ONLY over HTTPS to Render FastAPI, claims approved execution
jobs transactionally, executes them inside localhost Docker Judge0 CE, and
returns sanitized results over HTTPS.

Security invariants:
- Never exposes any inbound port.
- Never requires DATABASE_URL or SUPABASE_SERVICE_ROLE_KEY.
- Refuses non-loopback JUDGE0_BASE_URL.
- Refuses non-HTTPS remote API URLs (allows http://localhost / 127.0.0.1 only for local tests).
- Never prints or logs secret tokens.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import signal
import socket
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

# Ensure backend/app is importable when launched directly
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.core.config import Settings  # noqa: E402
from app.core.errors import AppError  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.integrations.execution.router import ResilientExecutionClient  # noqa: E402
from app.integrations.judge0.client import HttpJudge0Client, Judge0Client  # noqa: E402
from app.integrations.piston.client import HttpPistonClient, is_piston_configured  # noqa: E402

logger = get_logger("thinkfirst.execution_worker")

SUPPORTED_SLUGS = ["python", "javascript", "c", "cpp", "java"]
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def _validate_urls(api_base_url: str, judge0_base_url: str) -> None:
    api_parsed = urlparse(api_base_url)
    if api_parsed.scheme not in ("https", "http") or not api_parsed.netloc:
        raise ValueError("THINKFIRST_API_BASE_URL must be a valid URL.")
    if api_parsed.scheme != "https" and (api_parsed.hostname or "").lower() not in _LOOPBACK_HOSTS:
        raise ValueError("THINKFIRST_API_BASE_URL must use HTTPS for non-local hosts.")

    j0_parsed = urlparse(judge0_base_url)
    if (j0_parsed.hostname or "").lower() not in _LOOPBACK_HOSTS:
        raise ValueError(
            "JUDGE0_BASE_URL must point to localhost / 127.0.0.1 for the local code runner."
        )


class OutboundExecutionWorker:
    """Polls Render over outbound HTTPS and executes jobs on localhost Judge0."""

    def __init__(
        self,
        *,
        api_base_url: str,
        worker_id: str,
        worker_token: str,
        judge0_base_url: str,
        judge0_auth_token: str,
        poll_wait_seconds: int = 8,
        idle_sleep_seconds: float = 2.0,
        max_idle_sleep_seconds: float = 6.0,
        stop_signal_path: Path | None = None,
        display_name: str | None = None,
        piston_base_url: str | None = None,
        piston_fallback_enabled: bool = False,
    ) -> None:
        _validate_urls(api_base_url, judge0_base_url)
        if len(worker_token.strip()) < 24:
            raise ValueError("EXECUTION_WORKER_TOKEN must be at least 24 characters.")
        if piston_fallback_enabled and piston_base_url:
            p_parsed = urlparse(piston_base_url)
            if (p_parsed.hostname or "").lower() not in _LOOPBACK_HOSTS:
                raise ValueError(
                    "PISTON_BASE_URL must point to localhost / 127.0.0.1 for the local code runner."
                )

        self._api_base = api_base_url.rstrip("/")
        self._worker_id = worker_id.strip()
        self._worker_token = worker_token.strip()
        self._judge0_base = judge0_base_url.rstrip("/")
        self._judge0_token = judge0_auth_token.strip()
        self._display_name = display_name or f"Windows Judge0 Runner ({socket.gethostname()})"
        self._poll_wait = max(0, min(poll_wait_seconds, 12))
        self._idle_sleep = max(0.5, idle_sleep_seconds)
        self._max_idle_sleep = max(self._idle_sleep, max_idle_sleep_seconds)
        self._stop_signal_path = stop_signal_path
        self._stop_requested = False
        self._judge0_version: str | None = None

        self._judge0_settings = Settings(
            _env_file=None,
            app_env="development",
            judge0_base_url=self._judge0_base,
            judge0_auth_mode="auth_token",
            judge0_auth_token=self._judge0_token,
            judge0_http_timeout_seconds=15.0,
            judge0_poll_interval_seconds=0.35,
            judge0_poll_timeout_seconds=20.0,
            judge0_max_retries=2,
            execution_fallback_enabled=bool(piston_fallback_enabled and piston_base_url),
            piston_enabled=bool(piston_fallback_enabled and piston_base_url),
            piston_base_url=(piston_base_url or "http://127.0.0.1:2000").rstrip("/"),
        )
        primary_judge0 = HttpJudge0Client(self._judge0_settings)
        fallback_piston = (
            HttpPistonClient(self._judge0_settings)
            if is_piston_configured(self._judge0_settings)
            else None
        )
        self._judge0: Judge0Client = (
            ResilientExecutionClient(
                primary=primary_judge0,
                fallback=fallback_piston,
                settings=self._judge0_settings,
            )
            if fallback_piston is not None
            else primary_judge0
        )

    def _worker_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Worker-Id": self._worker_id,
            "X-Worker-Token": self._worker_token,
        }

    def request_stop(self) -> None:
        self._stop_requested = True

    def _should_stop(self) -> bool:
        if self._stop_requested:
            return True
        if self._stop_signal_path and self._stop_signal_path.exists():
            self._stop_requested = True
            return True
        return False

    async def check_local_judge0(self) -> str:
        headers = {"X-Auth-Token": self._judge0_token} if self._judge0_token else {}
        async with httpx.AsyncClient(timeout=8.0) as client:
            cfg_resp = await client.get(f"{self._judge0_base}/config_info", headers=headers)
            if cfg_resp.status_code == 401:
                raise RuntimeError("Local Judge0 rejected X-Auth-Token (HTTP 401).")
            cfg_resp.raise_for_status()
            about_resp = await client.get(f"{self._judge0_base}/about", headers=headers)
            about_resp.raise_for_status()
            version = str(about_resp.json().get("version", "1.13.1"))
            self._judge0_version = version
            return version

    async def send_heartbeat(self, client: httpx.AsyncClient) -> dict[str, Any]:
        resp = await client.post(
            f"{self._api_base}/api/v1/internal/execution-worker/heartbeat",
            headers=self._worker_headers(),
            json={
                "display_name": self._display_name,
                "judge0_version": self._judge0_version,
                "supported_languages": SUPPORTED_SLUGS,
                "active_job_count": 0,
            },
        )
        if resp.status_code == 401:
            raise RuntimeError("Production API rejected worker credentials (HTTP 401).")
        resp.raise_for_status()
        return dict(resp.json())

    async def send_offline(
        self, client: httpx.AsyncClient, reason: str = "graceful_shutdown"
    ) -> None:
        try:
            await client.post(
                f"{self._api_base}/api/v1/internal/execution-worker/offline",
                headers=self._worker_headers(),
                json={"reason": reason},
                timeout=8.0,
            )
        except Exception as exc:
            logger.warning("worker_offline_notify_failed", error_type=type(exc).__name__)

    async def check_local_piston(self) -> str:
        if not is_piston_configured(self._judge0_settings):
            raise RuntimeError("Local Piston fallback is not enabled.")
        piston_url = self._judge0_settings.piston_base_url.rstrip("/")
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{piston_url}/api/v2/runtimes")
            resp.raise_for_status()
            runtimes = resp.json()
            if not isinstance(runtimes, list) or not runtimes:
                raise RuntimeError("Local Piston returned no installed runtimes.")
            version = f"piston-fallback ({len(runtimes)} runtimes)"
            self._judge0_version = version
            return version

    async def check_local_providers(self) -> str:
        """Check local Judge0, falling back to local Piston only when fallback is enabled."""
        try:
            return await self.check_local_judge0()
        except Exception as judge0_exc:
            if not is_piston_configured(self._judge0_settings):
                raise
            logger.warning(
                "local_judge0_unavailable_checking_piston_fallback",
                error_type=type(judge0_exc).__name__,
            )
            try:
                return await self.check_local_piston()
            except Exception as piston_exc:
                raise RuntimeError(
                    f"Neither local Judge0 ({type(judge0_exc).__name__}) nor Piston fallback "
                    f"({type(piston_exc).__name__}) is healthy."
                ) from piston_exc

    async def self_check(self) -> bool:
        """Verify local Judge0 (or Piston fallback), API readiness, and worker queue auth."""
        version = await self.check_local_providers()
        logger.info("local_execution_provider_ready", version=version, url=self._judge0_base)

        async with httpx.AsyncClient(timeout=45.0) as client:
            ready_resp = await client.get(f"{self._api_base}/health/ready")
            ready_resp.raise_for_status()
            ready_json = ready_resp.json()
            if ready_json.get("database") != "ok":
                raise RuntimeError(f"Production backend database not ready: {ready_json}")

            hb = await self.send_heartbeat(client)
            logger.info(
                "production_worker_auth_verified",
                worker_id=hb.get("worker_id"),
                queue_depth=hb.get("queue_depth"),
            )
        return True

    async def _lease_keeper(
        self,
        client: httpx.AsyncClient,
        job_id: str,
        claim_token: str,
        done_event: asyncio.Event,
    ) -> None:
        while not done_event.is_set() and not self._should_stop():
            try:
                await asyncio.wait_for(done_event.wait(), timeout=15.0)
                return
            except TimeoutError:
                pass
            try:
                resp = await client.post(
                    f"{self._api_base}/api/v1/internal/execution-worker/jobs/{job_id}/renew",
                    headers=self._worker_headers(),
                    json={"claim_token": claim_token},
                    timeout=10.0,
                )
                if resp.status_code == 200 and not resp.json().get("renewed", False):
                    return
            except Exception as exc:
                logger.warning(
                    "worker_lease_renew_failed",
                    job_id=job_id,
                    error_type=type(exc).__name__,
                )

    async def _execute_claimed_job(self, client: httpx.AsyncClient, job: dict[str, Any]) -> None:
        job_id = str(job["job_id"])
        claim_token = str(job["claim_token"])
        lang_id = int(job["judge0_language_id"])
        lang_slug = str(job["language_slug"])
        source_code = str(job["source_code"])
        cpu_limit = float(job.get("cpu_time_limit_seconds", 2.0))
        mem_limit = int(job.get("memory_limit_kb", 131072))
        test_cases = list(job.get("test_cases") or [])

        logger.info(
            "worker_executing_job",
            job_id=job_id,
            language_slug=lang_slug,
            test_count=len(test_cases),
        )

        outcomes: list[dict[str, Any]] = []
        engine_error: str | None = None
        error_code: str | None = None
        done_event = asyncio.Event()
        keeper_task = asyncio.create_task(
            self._lease_keeper(client, job_id, claim_token, done_event)
        )

        try:
            for tc in test_cases:
                res = await self._judge0.execute_test_case(
                    source_code=source_code,
                    judge0_language_id=lang_id,
                    stdin=str(tc.get("stdin", "")),
                    expected_output=str(tc.get("expected_output", "")),
                    cpu_time_limit_seconds=cpu_limit,
                    memory_limit_kb=mem_limit,
                )
                outcomes.append(
                    {
                        "test_case_id": tc.get("test_case_id"),
                        "ordinal": int(tc.get("ordinal", 1)),
                        "is_hidden": bool(tc.get("is_hidden", False)),
                        "token": res.token,
                        "status_id": res.status_id,
                        "status_description": res.status_description,
                        "verdict": res.verdict,
                        "stdout": res.stdout[:131072] if res.stdout is not None else None,
                        "stderr": res.stderr[:131072] if res.stderr is not None else None,
                        "compile_output": (
                            res.compile_output[:131072] if res.compile_output is not None else None
                        ),
                        "runtime_ms": res.runtime_ms,
                        "memory_kb": res.memory_kb,
                        "execution_provider": res.execution_provider,
                    }
                )
                # Fast-fail remaining test cases on compilation error (identical compiler failure)
                if res.verdict == "compilation_error":
                    for rem in test_cases[len(outcomes) :]:
                        outcomes.append(
                            {
                                "test_case_id": rem.get("test_case_id"),
                                "ordinal": int(rem.get("ordinal", 1)),
                                "is_hidden": bool(rem.get("is_hidden", False)),
                                "token": res.token,
                                "status_id": res.status_id,
                                "status_description": res.status_description,
                                "verdict": "compilation_error",
                                "stdout": None,
                                "stderr": None,
                                "compile_output": (
                                    res.compile_output[:131072]
                                    if res.compile_output is not None
                                    else None
                                ),
                                "runtime_ms": None,
                                "memory_kb": None,
                                "execution_provider": res.execution_provider,
                            }
                        )
                    break
        except AppError as exc:
            engine_error = exc.message
            error_code = exc.code
            logger.error("worker_judge0_app_error", job_id=job_id, code=exc.code)
        except asyncio.CancelledError:
            # Release cleanly if cancelled mid-flight
            await self._release_job(client, job_id, claim_token, "worker_cancelled", requeue=True)
            raise
        except Exception as exc:
            engine_error = f"Local Judge0 execution error ({type(exc).__name__})."
            error_code = "LOCAL_JUDGE0_ERROR"
            logger.error("worker_judge0_unexpected_error", job_id=job_id, error=type(exc).__name__)
        finally:
            done_event.set()
            keeper_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await keeper_task

        result_payload: dict[str, Any] = {
            "claim_token": claim_token,
            "outcomes": outcomes,
            "engine_error": engine_error,
            "error_code": error_code,
        }
        resp = await client.post(
            f"{self._api_base}/api/v1/internal/execution-worker/jobs/{job_id}/result",
            headers=self._worker_headers(),
            json=result_payload,
            timeout=20.0,
        )
        if resp.status_code == 409:
            logger.warning("worker_job_claim_expired_or_duplicate", job_id=job_id)
            return
        resp.raise_for_status()
        body = resp.json()
        logger.info(
            "worker_job_completed",
            job_id=job_id,
            status=body.get("status"),
            verdict=body.get("verdict"),
        )

    async def _release_job(
        self,
        client: httpx.AsyncClient,
        job_id: str,
        claim_token: str,
        reason: str,
        *,
        requeue: bool = True,
    ) -> None:
        try:
            await client.post(
                f"{self._api_base}/api/v1/internal/execution-worker/jobs/{job_id}/release",
                headers=self._worker_headers(),
                json={"claim_token": claim_token, "reason": reason, "requeue": requeue},
                timeout=10.0,
            )
        except Exception as exc:
            logger.warning("worker_release_failed", job_id=job_id, error=type(exc).__name__)

    async def run_forever(self, *, max_cycles: int | None = None) -> None:
        """Main bounded long-poll loop with graceful shutdown and backoff."""
        if self._stop_signal_path and self._stop_signal_path.exists():
            self._stop_signal_path.unlink(missing_ok=True)

        await self.check_local_providers()
        current_idle = self._idle_sleep
        error_backoff = 3.0
        cycles = 0

        async with httpx.AsyncClient(timeout=max(45.0, float(self._poll_wait) + 20.0)) as client:
            try:
                while not self._should_stop():
                    if max_cycles is not None and cycles >= max_cycles:
                        break
                    cycles += 1
                    try:
                        claim_resp = await client.post(
                            f"{self._api_base}/api/v1/internal/execution-worker/claim",
                            headers=self._worker_headers(),
                            json={
                                "display_name": self._display_name,
                                "judge0_version": self._judge0_version,
                                "supported_languages": SUPPORTED_SLUGS,
                                "wait_seconds": self._poll_wait,
                            },
                        )
                        if claim_resp.status_code == 401:
                            logger.error("worker_auth_rejected_401")
                            raise RuntimeError("Worker token rejected by production API (401).")
                        if claim_resp.status_code == 429:
                            await asyncio.sleep(min(error_backoff, 15.0))
                            error_backoff = min(error_backoff * 1.5, 20.0)
                            continue
                        claim_resp.raise_for_status()
                        error_backoff = 3.0

                        data = claim_resp.json()
                        job = data.get("job")
                        if job is not None:
                            await self._execute_claimed_job(client, job)
                            current_idle = self._idle_sleep
                            await asyncio.sleep(0.2)
                        else:
                            # Bounded gentle backoff while idle
                            sleep_for = min(current_idle, self._max_idle_sleep)
                            current_idle = min(current_idle * 1.25, self._max_idle_sleep)
                            # Sleep in 0.5s slices so stop signal reacts quickly
                            remaining = sleep_for
                            while remaining > 0 and not self._should_stop():
                                step = min(0.5, remaining)
                                await asyncio.sleep(step)
                                remaining -= step
                    except RuntimeError:
                        raise
                    except Exception as exc:
                        logger.warning(
                            "worker_poll_error_retrying",
                            error_type=type(exc).__name__,
                            backoff_seconds=error_backoff,
                        )
                        remaining = error_backoff
                        while remaining > 0 and not self._should_stop():
                            step = min(0.5, remaining)
                            await asyncio.sleep(step)
                            remaining -= step
                        error_backoff = min(error_backoff * 1.5, 20.0)
            finally:
                logger.info("worker_shutting_down", worker_id=self._worker_id)
                await self.send_offline(client, reason="graceful_shutdown")
                if self._stop_signal_path and self._stop_signal_path.exists():
                    self._stop_signal_path.unlink(missing_ok=True)


def _default_env_path() -> Path:
    local_app = os.environ.get("LOCALAPPDATA")
    if local_app:
        return Path(local_app) / "ThinkFirstCodeRunner" / "runner.env"
    return Path.home() / ".thinkfirst_code_runner" / "runner.env"


def _default_stop_signal_path(env_file: Path) -> Path:
    return env_file.parent / "stop.signal"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ThinkFirst Local Outbound Judge0 Execution Worker"
    )
    parser.add_argument("--env-file", type=Path, default=_default_env_path())
    parser.add_argument(
        "--self-check", action="store_true", help="Verify Judge0 + Render auth and exit"
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_level)
    _load_env_file(args.env_file)

    api_url = os.environ.get(
        "THINKFIRST_API_BASE_URL", "https://codementor-ai-backend-6sbr.onrender.com"
    )
    worker_id = os.environ.get("EXECUTION_WORKER_ID", f"win-{socket.gethostname().lower()[:24]}")
    worker_token = os.environ.get("EXECUTION_WORKER_TOKEN", "")
    judge0_url = os.environ.get("JUDGE0_BASE_URL", "http://127.0.0.1:2359")
    judge0_token = os.environ.get("JUDGE0_AUTH_TOKEN", "")
    poll_wait = int(os.environ.get("WORKER_POLL_WAIT_SECONDS", "8"))
    idle_sleep = float(os.environ.get("WORKER_IDLE_SLEEP_SECONDS", "2"))
    max_idle = float(os.environ.get("WORKER_MAX_IDLE_SLEEP_SECONDS", "6"))
    piston_url = os.environ.get("PISTON_BASE_URL", "http://127.0.0.1:2000")
    piston_fallback = os.environ.get("PISTON_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }

    worker = OutboundExecutionWorker(
        api_base_url=api_url,
        worker_id=worker_id,
        worker_token=worker_token,
        judge0_base_url=judge0_url,
        judge0_auth_token=judge0_token,
        poll_wait_seconds=poll_wait,
        idle_sleep_seconds=idle_sleep,
        max_idle_sleep_seconds=max_idle,
        stop_signal_path=_default_stop_signal_path(args.env_file),
        piston_base_url=piston_url,
        piston_fallback_enabled=piston_fallback,
    )

    if args.self_check:
        try:
            asyncio.run(worker.self_check())
            print("READY: Local Judge0 and production execution queue verified.")
            return 0
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    def _handle_sig(_signum: int, _frame: Any) -> None:
        worker.request_stop()

    signal.signal(signal.SIGINT, _handle_sig)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_sig)

    try:
        asyncio.run(worker.run_forever())
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
