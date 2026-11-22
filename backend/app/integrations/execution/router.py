"""Resilient execution provider router: Judge0 CE Primary + Self-hosted Piston Fallback.

Strict Fallback Contract:
- Judge0 CE is ALWAYS attempted first when configured.
- Student code verdicts (accepted, wrong_answer, compilation_error, runtime_error,
  time_limit_exceeded, memory_limit_exceeded) NEVER trigger fallback to Piston.
- ONLY provider/infrastructure failures (Judge0 unreachable, connection refused,
  timeout, HTTP 5xx, HTTP 429 rate-limit, or Judge0 disabled/misconfigured)
  trigger fallback to self-hosted Piston.
- If BOTH Judge0 and Piston are unavailable, a clear 503 AppError is raised without
  faking success or creating duplicate submissions.
"""

from __future__ import annotations

import httpx
from fastapi import status

from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import get_logger
from app.integrations.judge0.client import (
    Judge0Client,
    Judge0ExecutionOutcome,
    Judge0Language,
)
from app.integrations.piston.client import (
    JUDGE0_ID_TO_SLUG,
    PistonClient,
    is_piston_configured,
)

logger = get_logger(__name__)

_FALLBACK_TRIGGER_ERROR_CODES = frozenset(
    {
        "EXECUTION_SERVICE_UNAVAILABLE",
        "EXECUTION_RATE_LIMITED",
        "EXECUTION_SERVICE_ERROR",
    }
)


_JUDGE0_SANDBOX_INFRA_SIGNATURES: tuple[str, ...] = (
    "fatal process oom in coderange setup",
    "error occurred during initialization of vm",
    "could not reserve enough space for",
    "could not allocate metaspace",
    "no such file or directory @ rb_sysopen - /box/",
)


def _is_sandbox_infrastructure_outcome(outcome: Judge0ExecutionOutcome) -> bool:
    """Detect Judge0 sandbox/VM startup failures (NOT student code mistakes)."""
    if outcome.status_id == 13 or outcome.verdict == "internal_error":
        return True
    combined = f"{outcome.compile_output or ''}\n{outcome.stderr or ''}".lower()
    return any(sig in combined for sig in _JUDGE0_SANDBOX_INFRA_SIGNATURES)


def _is_provider_outage(exc: Exception) -> bool:
    if isinstance(exc, AppError):
        return exc.code in _FALLBACK_TRIGGER_ERROR_CODES or exc.status_code in (
            status.HTTP_429_TOO_MANY_REQUESTS,
            status.HTTP_502_BAD_GATEWAY,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            status.HTTP_504_GATEWAY_TIMEOUT,
        )
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500 or exc.response.status_code == 429
    return False


class ResilientExecutionClient:
    """Implements Judge0Client protocol with strict infrastructure-only fallback to Piston."""

    def __init__(
        self,
        *,
        primary: Judge0Client,
        fallback: PistonClient | None,
        settings: Settings,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._settings = settings

    async def list_languages(self) -> list[Judge0Language]:
        return await self._primary.list_languages()

    async def execute_test_case(
        self,
        *,
        source_code: str,
        judge0_language_id: int,
        stdin: str,
        expected_output: str,
        cpu_time_limit_seconds: float,
        memory_limit_kb: int,
        language_slug: str | None = None,
    ) -> Judge0ExecutionOutcome:
        # 1. Primary provider: Judge0 CE
        try:
            outcome = await self._primary.execute_test_case(
                source_code=source_code,
                judge0_language_id=judge0_language_id,
                stdin=stdin,
                expected_output=expected_output,
                cpu_time_limit_seconds=cpu_time_limit_seconds,
                memory_limit_kb=memory_limit_kb,
            )
            if _is_sandbox_infrastructure_outcome(outcome):
                raise AppError(
                    code="EXECUTION_SERVICE_UNAVAILABLE",
                    message=(
                        "Primary sandbox runtime failed to initialize the language VM "
                        f"(status_id={outcome.status_id})."
                    ),
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            # NEVER trigger fallback on normal student execution verdicts.
            return outcome
        except Exception as primary_exc:
            if not _is_provider_outage(primary_exc):
                raise

            resolved_slug = language_slug or JUDGE0_ID_TO_SLUG.get(judge0_language_id)
            can_fallback = (
                self._fallback is not None
                and is_piston_configured(self._settings)
                and resolved_slug is not None
            )
            if not can_fallback:
                logger.error(
                    "execution_primary_failed_no_fallback",
                    language_slug=resolved_slug,
                    judge0_language_id=judge0_language_id,
                    error_type=type(primary_exc).__name__,
                )
                if isinstance(primary_exc, AppError):
                    raise
                raise AppError(
                    code="EXECUTION_SERVICE_UNAVAILABLE",
                    message=(
                        "Code execution service is currently unavailable. Please try again shortly."
                    ),
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                ) from primary_exc

            logger.warning(
                "execution_fallback_triggered",
                primary_provider="judge0",
                fallback_provider="piston",
                language_slug=resolved_slug,
                primary_error_code=getattr(primary_exc, "code", type(primary_exc).__name__),
            )

            assert self._fallback is not None and resolved_slug is not None
            try:
                return await self._fallback.execute_test_case(
                    source_code=source_code,
                    language_slug=resolved_slug,
                    stdin=stdin,
                    expected_output=expected_output,
                    cpu_time_limit_seconds=cpu_time_limit_seconds,
                    memory_limit_kb=memory_limit_kb,
                )
            except Exception as fallback_exc:
                logger.error(
                    "execution_both_providers_unavailable",
                    language_slug=resolved_slug,
                    primary_error=type(primary_exc).__name__,
                    fallback_error=type(fallback_exc).__name__,
                )
                raise AppError(
                    code="EXECUTION_SERVICE_UNAVAILABLE",
                    message=(
                        "Both primary (Judge0) and fallback (Piston) code execution services "
                        "are currently unavailable. Please try again shortly."
                    ),
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                ) from fallback_exc
