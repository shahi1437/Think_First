"""Security, authorization, deduplication, quota, and worker protocol tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.deps import (
    get_current_user,
    get_execution_service,
    get_execution_worker_service,
)
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.integrations.judge0.client import HttpJudge0Client
from app.main import create_app
from app.repositories.identity import UserRecord
from app.schemas.execution_queue import ExecutionAvailabilityResponse, WorkerClaimResponse
from app.schemas.problems import SubmissionCreateRequest
from app.services.execution.service import ExecutionService
from worker.execution_worker import OutboundExecutionWorker

_STRONG_WORKER_TOKEN = "wkr_test_super_secret_token_0123456789abcdef"


def _make_user(email: str = "student@thinkfirst.edu", roles: list[str] | None = None) -> UserRecord:
    return UserRecord(
        id=uuid4(),
        email=email,
        full_name="Test Learner",
        avatar_url=None,
        roles=roles or ["student"],  # type: ignore[arg-type]
        onboarding_completed=True,
        onboarding_completed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )


def _worker_settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "test",
        "rate_limit_enabled": False,
        "judge0_auth_mode": "worker_queue",
        "execution_worker_token": _STRONG_WORKER_TOKEN,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_production_readiness_validates_worker_queue_mode() -> None:
    missing_tok = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://u:p@pooler.supabase.com:5432/postgres",
        supabase_url="https://vsmrwfoqqjvomtjpypyv.supabase.co",
        cors_origins=["https://think-first-pi.vercel.app"],
        judge0_auth_mode="worker_queue",
        execution_worker_token="too-short",
    )
    warnings = missing_tok.validate_production_readiness()
    assert any("EXECUTION_WORKER_TOKEN" in w for w in warnings)

    valid = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://u:p@pooler.supabase.com:5432/postgres",
        supabase_url="https://vsmrwfoqqjvomtjpypyv.supabase.co",
        cors_origins=["https://think-first-pi.vercel.app"],
        judge0_auth_mode="worker_queue",
        execution_worker_token=_STRONG_WORKER_TOKEN,
    )
    assert valid.validate_production_readiness() == []


def test_outbound_worker_enforces_https_and_loopback_judge0() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        OutboundExecutionWorker(
            api_base_url="http://codementor-ai-backend-6sbr.onrender.com",
            worker_id="win-test",
            worker_token=_STRONG_WORKER_TOKEN,
            judge0_base_url="http://127.0.0.1:2359",
            judge0_auth_token="tok",
        )

    with pytest.raises(ValueError, match="localhost"):
        OutboundExecutionWorker(
            api_base_url="https://codementor-ai-backend-6sbr.onrender.com",
            worker_id="win-test",
            worker_token=_STRONG_WORKER_TOKEN,
            judge0_base_url="http://192.168.1.50:2359",
            judge0_auth_token="tok",
        )

    with pytest.raises(ValueError, match="24 characters"):
        OutboundExecutionWorker(
            api_base_url="https://codementor-ai-backend-6sbr.onrender.com",
            worker_id="win-test",
            worker_token="short",
            judge0_base_url="http://127.0.0.1:2359",
            judge0_auth_token="tok",
        )

    ok_worker = OutboundExecutionWorker(
        api_base_url="https://codementor-ai-backend-6sbr.onrender.com",
        worker_id="win-test",
        worker_token=_STRONG_WORKER_TOKEN,
        judge0_base_url="http://127.0.0.1:2359",
        judge0_auth_token="tok",
    )
    assert ok_worker is not None


@pytest.mark.asyncio
async def test_worker_and_execution_status_auth_enforcement() -> None:
    settings = _worker_settings()
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings

    fake_worker_svc = MagicMock()
    fake_worker_svc.claim_job = AsyncMock(
        return_value=WorkerClaimResponse(job=None, poll_after_seconds=2.0)
    )
    fake_worker_svc.get_availability = AsyncMock(
        return_value=ExecutionAvailabilityResponse(
            mode="worker_queue",
            available=True,
            worker_online=True,
            active_workers=1,
            queue_depth=0,
            last_heartbeat_at=datetime.now(UTC),
            message="Online",
        )
    )
    app.dependency_overrides[get_execution_worker_service] = lambda: fake_worker_svc

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Unauthenticated student status rejected (401)
        r_status_anon = await client.get("/api/v1/execution/status")
        assert r_status_anon.status_code == 401

        # 2. Unauthenticated worker claim rejected (401)
        r_no_tok = await client.post("/api/v1/internal/execution-worker/claim", json={})
        assert r_no_tok.status_code == 401
        assert r_no_tok.json()["code"] == "WORKER_AUTH_FAILED"

        # 3. Wrong worker token rejected (401) without leaking token
        r_bad_tok = await client.post(
            "/api/v1/internal/execution-worker/claim",
            headers={"X-Worker-Token": "wrong-token-value", "X-Worker-Id": "win-pc"},
            json={},
        )
        assert r_bad_tok.status_code == 401
        assert _STRONG_WORKER_TOKEN not in r_bad_tok.text

        # 4. Valid token + malformed worker ID rejected (400)
        r_bad_id = await client.post(
            "/api/v1/internal/execution-worker/claim",
            headers={"X-Worker-Token": _STRONG_WORKER_TOKEN, "X-Worker-Id": "../bad id!"},
            json={},
        )
        assert r_bad_id.status_code == 400
        assert r_bad_id.json()["code"] == "INVALID_WORKER_ID"

        # 5. Valid worker credentials accepted (200)
        r_ok = await client.post(
            "/api/v1/internal/execution-worker/claim",
            headers={"X-Worker-Token": _STRONG_WORKER_TOKEN, "X-Worker-Id": "win-shahi"},
            json={"wait_seconds": 0},
        )
        assert r_ok.status_code == 200
        assert r_ok.json()["job"] is None

        # 6. Authenticated student sees non-sensitive execution status (no worker tokens)
        app.dependency_overrides[get_current_user] = lambda: _make_user()
        r_status = await client.get("/api/v1/execution/status")
        assert r_status.status_code == 200
        assert r_status.json()["worker_online"] is True
        assert _STRONG_WORKER_TOKEN not in r_status.text


@pytest.mark.asyncio
async def test_worker_queue_offline_dedup_quota_allowlist_and_ownership() -> None:
    problem_id = uuid4()
    version_id = uuid4()
    tc_id = uuid4()
    student_a = _make_user("allowed@thinkfirst.edu")
    student_b = _make_user("blocked@thinkfirst.edu")

    problem_repo = MagicMock()
    problem_repo.get_quota_counts = AsyncMock(return_value=(0, 0))
    problem_repo.get_published_problem = AsyncMock(
        return_value=(
            SimpleNamespace(id=problem_id),
            SimpleNamespace(
                id=version_id,
                mode="coding",
                time_limit_ms=2000,
                memory_limit_kb=131072,
                variants=[SimpleNamespace(language_slug="python")],
                test_cases=[
                    SimpleNamespace(
                        id=tc_id,
                        ordinal=1,
                        name="Public 1",
                        input_data="1 2",
                        expected_output="3",
                        is_hidden=False,
                    )
                ],
            ),
        )
    )
    problem_repo.get_language_by_slug = AsyncMock(
        return_value=SimpleNamespace(slug="python", is_enabled=True, judge0_language_id=71)
    )
    problem_repo.create_submission = AsyncMock()
    problem_repo.save_revision = AsyncMock()

    queue_repo = MagicMock()
    queue_repo.sweep_expired_and_stale_jobs = AsyncMock(return_value=0)
    queue_repo.get_online_workers_summary = AsyncMock(return_value=(0, None, 0))

    settings = _worker_settings(execution_allowed_emails=["allowed@thinkfirst.edu"])
    service = ExecutionService(
        repository=problem_repo,
        judge0=HttpJudge0Client(settings),
        settings=settings,
        queue_repository=queue_repo,
    )
    req = SubmissionCreateRequest(
        problem_id=problem_id,
        language_slug="python",
        submission_kind="run",
        source_code="print(3)",
    )

    # 1. Non-allowlisted user blocked with 403
    with pytest.raises(AppError) as restricted_exc:
        await service.execute_submission(user=student_b, payload=req)
    assert restricted_exc.value.status_code == 403
    assert restricted_exc.value.code == "EXECUTION_RESTRICTED"

    # 2. Offline local worker fails cleanly with 503 before creating any submission row
    with pytest.raises(AppError) as offline_exc:
        await service.execute_submission(user=student_a, payload=req)
    assert offline_exc.value.status_code == 503
    assert offline_exc.value.code == "EXECUTION_SERVICE_UNAVAILABLE"
    problem_repo.create_submission.assert_not_awaited()

    # 3. Duplicate in-flight submission returns existing queued submission cleanly
    existing_sub_id = uuid4()
    existing_sub = SimpleNamespace(
        id=existing_sub_id,
        student_id=student_a.id,
        problem_id=problem_id,
        problem_version_id=version_id,
        language_slug="python",
        submission_kind="run",
        source_code="print(3)",
        prediction_text=None,
        explanation_text=None,
        status="queued",
        verdict="pending",
        passed_tests=0,
        total_tests=1,
        runtime_ms=None,
        memory_kb=None,
        execution_provider="judge0",
        execution_evidence={},
        results=[],
        created_at=datetime.now(UTC),
    )
    queue_repo.get_online_workers_summary = AsyncMock(return_value=(1, datetime.now(UTC), 1))
    queue_repo.find_active_duplicate_submission_id = AsyncMock(return_value=existing_sub_id)
    problem_repo.get_submission_by_id = AsyncMock(return_value=existing_sub)

    dedup_resp = await service.execute_submission(
        user=student_a, payload=req, wait_for_completion=False
    )
    assert dedup_resp.id == existing_sub_id
    assert dedup_resp.status == "queued"
    problem_repo.create_submission.assert_not_awaited()

    # 4. Concurrent per-user active job cap enforced (429)
    queue_repo.find_active_duplicate_submission_id = AsyncMock(return_value=None)
    queue_repo.count_user_active_jobs = AsyncMock(return_value=2)
    with pytest.raises(AppError) as conc_exc:
        await service.execute_submission(user=student_a, payload=req)
    assert conc_exc.value.status_code == 429
    assert conc_exc.value.code == "CONCURRENT_EXECUTION_LIMIT"

    # 5. Job ownership enforced on cancel_submission (Student B cannot cancel Student A's job)
    with pytest.raises(AppError) as own_exc:
        await service.cancel_submission(user=student_b, submission_id=existing_sub_id)
    assert own_exc.value.status_code == 403
    assert own_exc.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_cancel_submission_route_requires_auth() -> None:
    app = create_app(Settings(app_env="test", rate_limit_enabled=False))
    app.dependency_overrides[get_execution_service] = lambda: MagicMock()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(f"/api/v1/submissions/{uuid4()}/cancel")
    assert res.status_code == 401
    assert timedelta(seconds=1).total_seconds() == 1.0
