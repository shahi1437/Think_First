"""Self-hosted Piston v2 async HTTP client for secure fallback code execution."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from fastapi import status

from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.integrations.judge0.client import Judge0ExecutionOutcome, Verdict

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PistonRuntime:
    language: str
    version: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _PistonLanguageSpec:
    slug: str
    piston_language: str
    filename: str
    aliases: tuple[str, ...]
    allow_rlimit_as: bool


_LANGUAGE_SPECS_BY_SLUG: dict[str, _PistonLanguageSpec] = {
    "python": _PistonLanguageSpec(
        slug="python",
        piston_language="python",
        filename="main.py",
        aliases=("python", "python3", "py"),
        allow_rlimit_as=True,
    ),
    "javascript": _PistonLanguageSpec(
        slug="javascript",
        piston_language="javascript",
        filename="main.js",
        aliases=("javascript", "js", "node", "node-javascript"),
        allow_rlimit_as=False,
    ),
    "c": _PistonLanguageSpec(
        slug="c",
        piston_language="c",
        filename="main.c",
        aliases=("c", "gcc"),
        allow_rlimit_as=True,
    ),
    "cpp": _PistonLanguageSpec(
        slug="cpp",
        piston_language="c++",
        filename="main.cpp",
        aliases=("c++", "cpp", "g++"),
        allow_rlimit_as=True,
    ),
    "java": _PistonLanguageSpec(
        slug="java",
        piston_language="java",
        filename="Main.java",
        aliases=("java",),
        allow_rlimit_as=False,
    ),
}

JUDGE0_ID_TO_SLUG: dict[int, str] = {
    71: "python",
    63: "javascript",
    50: "c",
    54: "cpp",
    62: "java",
}


class PistonClient(Protocol):
    """Protocol for self-hosted Piston fallback code execution."""

    async def list_runtimes(self) -> list[PistonRuntime]: ...

    async def execute_test_case(
        self,
        *,
        source_code: str,
        language_slug: str,
        stdin: str,
        expected_output: str,
        cpu_time_limit_seconds: float,
        memory_limit_kb: int,
    ) -> Judge0ExecutionOutcome: ...


def is_piston_configured(settings: Settings) -> bool:
    """Return True only when self-hosted Piston fallback is safely enabled and configured."""
    base_url = (settings.piston_base_url or "").strip()
    if not (settings.execution_fallback_enabled and settings.piston_enabled and base_url):
        return False
    if settings.app_env == "production":
        lowered = base_url.lower()
        if (
            not settings.piston_isolated_host_verified
            or "127.0.0.1" in lowered
            or "localhost" in lowered
        ):
            return False
    return True


def _truncate_output(value: str | None, max_bytes: int) -> str | None:
    if value is None:
        return None
    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return value
    return encoded[:max_bytes].decode("utf-8", errors="replace") + "\n...[output truncated]"


def _match_runtime(
    spec: _PistonLanguageSpec, runtimes: list[PistonRuntime]
) -> PistonRuntime | None:
    alias_set = {a.lower() for a in spec.aliases}
    for rt in runtimes:
        if rt.language.lower() in alias_set:
            return rt
        if any(a.lower() in alias_set for a in rt.aliases):
            return rt
    return None


class HttpPistonClient:
    """Async HTTP client for self-hosted Piston v2 bound to a private loopback/internal URL."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base_url = (settings.piston_base_url or "").rstrip("/")
        self._timeout = max(settings.piston_http_timeout_seconds, 2.0)
        self._max_output = max(settings.piston_max_output_bytes, 4096)
        self._cached_runtimes: list[PistonRuntime] | None = None
        self._cached_at: float = 0.0

    def _ensure_configured(self) -> None:
        if not is_piston_configured(self._settings):
            raise AppError(
                code="PISTON_EXECUTION_UNAVAILABLE",
                message="Fallback execution provider (Piston) is disabled or not configured.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    async def list_runtimes(self) -> list[PistonRuntime]:
        self._ensure_configured()
        try:
            async with httpx.AsyncClient(timeout=min(self._timeout, 5.0)) as client:
                resp = await client.get(f"{self._base_url}/api/v2/runtimes")
                resp.raise_for_status()
                items = resp.json()
        except Exception as exc:
            logger.warning("piston_runtimes_failed", error_type=type(exc).__name__)
            raise AppError(
                code="PISTON_EXECUTION_UNAVAILABLE",
                message="Fallback execution provider (Piston) is currently unreachable.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        runtimes: list[PistonRuntime] = []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                lang = str(item.get("language", "")).strip()
                ver = str(item.get("version", "")).strip()
                raw_aliases = item.get("aliases") or []
                aliases = tuple(str(a) for a in raw_aliases if isinstance(a, str))
                if lang and ver:
                    runtimes.append(PistonRuntime(language=lang, version=ver, aliases=aliases))
        self._cached_runtimes = runtimes
        self._cached_at = time.monotonic()
        return runtimes

    async def _resolve_runtime(self, spec: _PistonLanguageSpec) -> tuple[str, str]:
        now = time.monotonic()
        runtimes = self._cached_runtimes
        if runtimes is None or (now - self._cached_at) > 60.0:
            runtimes = await self.list_runtimes()
        matched = _match_runtime(spec, runtimes)
        if matched is None:
            raise AppError(
                code="PISTON_RUNTIME_MISSING",
                message=(
                    f"Fallback execution provider (Piston) does not have a runtime installed "
                    f"for '{spec.slug}'."
                ),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return matched.language, matched.version

    async def execute_test_case(
        self,
        *,
        source_code: str,
        language_slug: str,
        stdin: str,
        expected_output: str,
        cpu_time_limit_seconds: float,
        memory_limit_kb: int,
    ) -> Judge0ExecutionOutcome:
        self._ensure_configured()
        spec = _LANGUAGE_SPECS_BY_SLUG.get(language_slug)
        if spec is None:
            raise AppError(
                code="UNSUPPORTED_LANGUAGE",
                message=f"Language '{language_slug}' is not supported by Piston fallback.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        piston_lang, piston_version = await self._resolve_runtime(spec)

        # Piston `run_timeout` is wall-clock (includes JVM / Node runtime cold startup),
        # whereas Judge0's limit is CPU time. Add a bounded startup buffer for heavy VMs
        # while strictly capping at `piston_run_timeout_ms`.
        vm_startup_buffer_ms = (
            1500 if spec.slug == "java" else (500 if spec.slug == "javascript" else 0)
        )
        run_timeout_ms = min(
            max(int(cpu_time_limit_seconds * 1000) + vm_startup_buffer_ms, 1000),
            max(self._settings.piston_run_timeout_ms, 1000),
        )
        compile_timeout_ms = max(self._settings.piston_compile_timeout_ms, 3000)

        payload: dict[str, Any] = {
            "language": piston_lang,
            "version": piston_version,
            "files": [{"name": spec.filename, "content": source_code}],
            "stdin": stdin,
            "compile_timeout": compile_timeout_ms,
            "run_timeout": run_timeout_ms,
        }
        # Never send -1 ("unlimited"): hardened Piston servers with positive cgroup v2
        # memory limits reject negative overrides with HTTP 400. For Python/C/C++, pass
        # a bounded positive per-problem limit; for V8/JVM (JS/Java), defer to Piston's
        # server-side cgroup v2 PISTON_RUN_MEMORY_LIMIT cap.
        if spec.allow_rlimit_as:
            payload["run_memory_limit"] = min(max(memory_limit_kb * 1024, 67_108_864), 536_870_912)

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/api/v2/execute",
                    json=payload,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )
                if resp.status_code >= 500 or resp.status_code == 429:
                    raise AppError(
                        code="PISTON_EXECUTION_UNAVAILABLE",
                        message=f"Fallback execution provider returned HTTP {resp.status_code}.",
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )
                if resp.status_code >= 400:
                    detail = resp.text[:300]
                    logger.warning(
                        "piston_bad_request",
                        status_code=resp.status_code,
                        language=language_slug,
                        detail=detail,
                    )
                    raise AppError(
                        code="PISTON_EXECUTION_UNAVAILABLE",
                        message="Fallback execution provider could not execute this language.",
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )
                data = resp.json()
        except AppError:
            raise
        except Exception as exc:
            logger.error(
                "piston_request_failed",
                language=language_slug,
                error_type=type(exc).__name__,
            )
            raise AppError(
                code="PISTON_EXECUTION_UNAVAILABLE",
                message="Fallback execution provider (Piston) is currently unavailable.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        elapsed_ms = round((time.perf_counter() - started) * 1000)
        token = f"piston-{uuid.uuid4().hex[:16]}"

        compile_stage = data.get("compile")
        if isinstance(compile_stage, dict):
            c_code = compile_stage.get("code")
            c_signal = compile_stage.get("signal")
            if (c_code is not None and c_code != 0) or c_signal:
                compile_err = (
                    compile_stage.get("stderr")
                    or compile_stage.get("output")
                    or compile_stage.get("stdout")
                    or "Compilation failed."
                )
                return Judge0ExecutionOutcome(
                    token=token,
                    status_id=6,
                    status_description="Compilation Error (Piston)",
                    verdict="compilation_error",
                    stdout=None,
                    stderr=None,
                    compile_output=_truncate_output(str(compile_err), self._max_output),
                    runtime_ms=elapsed_ms,
                    memory_kb=None,
                    execution_provider="piston",
                )

        run_stage = data.get("run") or {}
        stdout = _truncate_output(
            str(run_stage.get("stdout")) if run_stage.get("stdout") is not None else "",
            self._max_output,
        )
        stderr = _truncate_output(
            str(run_stage.get("stderr")) if run_stage.get("stderr") else None,
            self._max_output,
        )
        run_code = run_stage.get("code")
        run_signal = run_stage.get("signal")
        run_message = str(run_stage.get("message") or "")

        verdict: Verdict
        status_id: int
        status_desc: str

        lower_msg = run_message.lower()
        lower_err = (stderr or "").lower()
        if (
            "memory" in lower_msg
            or "memoryerror" in lower_err
            or "outofmemoryerror" in lower_err
            or "std::bad_alloc" in lower_err
        ):
            verdict = "memory_limit_exceeded"
            status_id = 11
            status_desc = "Memory Limit Exceeded (Piston)"
        elif run_signal == "SIGKILL" or "timed out" in lower_msg or "timeout" in lower_msg:
            verdict = "time_limit_exceeded"
            status_id = 5
            status_desc = "Time Limit Exceeded (Piston)"
        elif (run_code is not None and run_code != 0) or run_signal:
            verdict = "runtime_error"
            status_id = 11
            status_desc = f"Runtime Error (Piston, exit={run_code}, signal={run_signal})"
        else:
            if (stdout or "").strip() == expected_output.strip():
                verdict = "accepted"
                status_id = 3
                status_desc = "Accepted (Piston)"
            else:
                verdict = "wrong_answer"
                status_id = 4
                status_desc = "Wrong Answer (Piston)"

        return Judge0ExecutionOutcome(
            token=token,
            status_id=status_id,
            status_description=status_desc,
            verdict=verdict,
            stdout=stdout,
            stderr=stderr,
            compile_output=None,
            runtime_ms=elapsed_ms,
            memory_kb=None,
            execution_provider="piston",
        )
