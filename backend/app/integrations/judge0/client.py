import asyncio
import base64
from dataclasses import dataclass
from typing import Any, Literal, Protocol

import httpx
from fastapi import status

from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

Verdict = Literal[
    "accepted",
    "wrong_answer",
    "compilation_error",
    "runtime_error",
    "time_limit_exceeded",
    "memory_limit_exceeded",
    "internal_error",
]


@dataclass(frozen=True, slots=True)
class Judge0Language:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class Judge0ExecutionOutcome:
    token: str
    status_id: int
    status_description: str
    verdict: Verdict
    stdout: str | None
    stderr: str | None
    compile_output: str | None
    runtime_ms: int | None
    memory_kb: int | None


class Judge0Client(Protocol):
    """Protocol for isolated code execution against Judge0 CE."""

    async def list_languages(self) -> list[Judge0Language]: ...

    async def execute_test_case(
        self,
        *,
        source_code: str,
        judge0_language_id: int,
        stdin: str,
        expected_output: str,
        cpu_time_limit_seconds: float,
        memory_limit_kb: int,
    ) -> Judge0ExecutionOutcome: ...


def _b64_encode(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def _b64_decode(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return base64.b64decode(value.encode("ascii")).decode("utf-8", errors="replace")
    except Exception:
        return value


def map_judge0_status_to_verdict(status_id: int, stderr: str | None) -> Verdict:
    """Map Judge0 CE numeric status codes to canonical platform verdicts."""
    if status_id == 3:
        return "accepted"
    if status_id == 4:
        return "wrong_answer"
    if status_id == 5:
        return "time_limit_exceeded"
    if status_id == 6:
        return "compilation_error"
    if status_id in (7, 8, 9, 10, 11, 12):
        if stderr and "MemoryError" in stderr:
            return "memory_limit_exceeded"
        return "runtime_error"
    return "internal_error"


class HttpJudge0Client:
    """Async HTTP client for Judge0 CE with base64 safety, bounded retries, and polling."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.judge0_base_url.rstrip("/")
        self._auth_token = settings.judge0_auth_token
        self._poll_interval = settings.judge0_poll_interval_seconds
        self._poll_timeout = settings.judge0_poll_timeout_seconds
        self._max_retries = settings.judge0_max_retries

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._auth_token:
            headers["X-Auth-Token"] = self._auth_token
        return headers

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await client.request(method, url, headers=self._headers(), **kwargs)
                if response.status_code >= 500 and attempt < self._max_retries:
                    await asyncio.sleep(0.3 * (attempt + 1))
                    continue
                response.raise_for_status()
                return response
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                last_exc = exc
                is_transient = isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)) or (
                    isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500
                )
                if is_transient and attempt < self._max_retries:
                    await asyncio.sleep(0.3 * (attempt + 1))
                    continue
                break

        logger.error("judge0_request_failed", error_type=type(last_exc).__name__)
        raise AppError(
            code="EXECUTION_SERVICE_UNAVAILABLE",
            message="Code execution service is currently unavailable.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from last_exc

    async def list_languages(self) -> list[Judge0Language]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await self._request_with_retry(client, "GET", f"{self._base_url}/languages")
            items = response.json()
            languages: list[Judge0Language] = []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and isinstance(item.get("id"), int):
                        languages.append(
                            Judge0Language(id=item["id"], name=str(item.get("name", "")))
                        )
            return languages

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
        payload = {
            "source_code": _b64_encode(source_code),
            "language_id": judge0_language_id,
            "stdin": _b64_encode(stdin),
            "expected_output": _b64_encode(expected_output),
            "cpu_time_limit": min(max(cpu_time_limit_seconds, 0.5), 10.0),
            "wall_time_limit": min(max(cpu_time_limit_seconds * 2.5, 2.0), 15.0),
            "memory_limit": min(max(memory_limit_kb, 16384), 524288),
            "max_processes_and_or_threads": 32,
            "enable_network": False,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            create_resp = await self._request_with_retry(
                client,
                "POST",
                f"{self._base_url}/submissions?base64_encoded=true&wait=false",
                json=payload,
            )
            token = create_resp.json().get("token")
            if not isinstance(token, str) or not token:
                raise AppError(
                    code="EXECUTION_SERVICE_ERROR",
                    message="Execution engine did not return a submission token.",
                    status_code=status.HTTP_502_BAD_GATEWAY,
                )

            deadline = asyncio.get_running_loop().time() + self._poll_timeout
            fields = "token,status,stdout,stderr,compile_output,time,memory,message"
            while True:
                poll_resp = await self._request_with_retry(
                    client,
                    "GET",
                    f"{self._base_url}/submissions/{token}?base64_encoded=true&fields={fields}",
                )
                data = poll_resp.json()
                status_obj = data.get("status") or {}
                status_id = int(status_obj.get("id", 13))
                status_desc = str(status_obj.get("description", "Unknown"))

                # Judge0 statuses 1 (In Queue) and 2 (Processing) are non-terminal
                if status_id >= 3:
                    stdout = _b64_decode(data.get("stdout"))
                    stderr = _b64_decode(data.get("stderr"))
                    compile_output = _b64_decode(data.get("compile_output"))
                    raw_time = data.get("time")
                    runtime_ms = round(float(raw_time) * 1000) if raw_time is not None else None
                    raw_mem = data.get("memory")
                    memory_kb = int(raw_mem) if raw_mem is not None else None

                    verdict = map_judge0_status_to_verdict(status_id, stderr)
                    # Normalize trailing whitespace differences safely when Judge0 returned 4
                    if (
                        verdict == "wrong_answer"
                        and stdout is not None
                        and stdout.strip() == expected_output.strip()
                    ):
                        verdict = "accepted"

                    return Judge0ExecutionOutcome(
                        token=token,
                        status_id=status_id,
                        status_description=status_desc,
                        verdict=verdict,
                        stdout=stdout,
                        stderr=stderr,
                        compile_output=compile_output,
                        runtime_ms=runtime_ms,
                        memory_kb=memory_kb,
                    )

                if asyncio.get_running_loop().time() >= deadline:
                    return Judge0ExecutionOutcome(
                        token=token,
                        status_id=5,
                        status_description="Execution Poll Timeout",
                        verdict="time_limit_exceeded",
                        stdout=None,
                        stderr="Execution timed out while polling sandbox.",
                        compile_output=None,
                        runtime_ms=int(self._poll_timeout * 1000),
                        memory_kb=None,
                    )

                await asyncio.sleep(self._poll_interval)
