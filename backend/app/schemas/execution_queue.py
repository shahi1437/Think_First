"""Pydantic schemas for outbound execution worker protocol and observability."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.problems import Verdict

ExecutionAvailabilityMode = Literal["direct_judge0", "worker_queue", "disabled"]
ExecutionJobStatus = Literal["queued", "running", "completed", "failed", "cancelled", "timed_out"]
ExecutionJobType = Literal["submission", "test_case"]


class ExecutionAvailabilityResponse(BaseModel):
    """Student/teacher/admin safe summary of live code execution readiness."""

    mode: ExecutionAvailabilityMode
    available: bool
    worker_online: bool
    active_workers: int = 0
    queue_depth: int = 0
    last_heartbeat_at: datetime | None = None
    message: str


class WorkerHeartbeatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(default="Local Judge0 Runner", min_length=1, max_length=100)
    judge0_version: str | None = Field(default=None, max_length=64)
    supported_languages: list[str] = Field(default_factory=list, max_length=20)
    active_job_count: int = Field(default=0, ge=0, le=32)
    last_error: str | None = Field(default=None, max_length=500)


class WorkerHeartbeatResponse(BaseModel):
    worker_id: str
    status: Literal["online", "draining", "offline"]
    queue_depth: int
    server_time: datetime


class WorkerClaimRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(default="Local Judge0 Runner", min_length=1, max_length=100)
    judge0_version: str | None = Field(default=None, max_length=64)
    supported_languages: list[str] = Field(default_factory=list, max_length=20)
    wait_seconds: int = Field(default=8, ge=0, le=12)


class WorkerJobTestCasePayload(BaseModel):
    test_case_id: UUID | None = None
    ordinal: int = Field(..., ge=1)
    stdin: str = ""
    expected_output: str = ""
    is_hidden: bool = False


class WorkerClaimedJobResponse(BaseModel):
    job_id: UUID
    job_type: ExecutionJobType
    submission_id: UUID | None = None
    claim_token: UUID
    language_slug: str
    judge0_language_id: int
    source_code: str
    cpu_time_limit_seconds: float
    memory_limit_kb: int
    test_cases: list[WorkerJobTestCasePayload]
    expires_at: datetime


class WorkerClaimResponse(BaseModel):
    job: WorkerClaimedJobResponse | None = None
    poll_after_seconds: float = 2.0


class WorkerTestCaseOutcomeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_case_id: UUID | None = None
    ordinal: int = Field(..., ge=1)
    is_hidden: bool = False
    token: str = Field(default="local-judge0", max_length=128)
    status_id: int = Field(..., ge=1, le=99)
    status_description: str = Field(default="", max_length=120)
    verdict: Verdict
    stdout: str | None = Field(default=None, max_length=131072)
    stderr: str | None = Field(default=None, max_length=131072)
    compile_output: str | None = Field(default=None, max_length=131072)
    runtime_ms: int | None = Field(default=None, ge=0, le=120000)
    memory_kb: int | None = Field(default=None, ge=0, le=8388608)
    execution_provider: Literal["judge0"] = "judge0"


class WorkerJobResultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_token: UUID
    outcomes: list[WorkerTestCaseOutcomeInput] = Field(default_factory=list, max_length=64)
    engine_error: str | None = Field(default=None, max_length=500)
    error_code: str | None = Field(default=None, max_length=64)


class WorkerJobResultResponse(BaseModel):
    job_id: UUID
    status: ExecutionJobStatus
    submission_id: UUID | None = None
    verdict: Verdict | None = None


class WorkerJobReleaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_token: UUID
    reason: str = Field(default="worker_shutdown", max_length=200)
    requeue: bool = True


class WorkerOfflineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(default="graceful_shutdown", max_length=200)
