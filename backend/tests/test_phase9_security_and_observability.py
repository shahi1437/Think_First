"""Phase 9 security hardening, rate limiting, and admin operations telemetry tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.deps import get_current_user
from app.core.config import Settings
from app.core.database import get_db_manager
from app.main import create_app
from app.repositories.identity import UserRecord


def _fake_user(*roles: str) -> UserRecord:
    return UserRecord(
        id=uuid4(),
        email=f"{roles[0]}@codementor.local",
        full_name=f"Test {roles[0].title()}",
        avatar_url=None,
        roles=list(roles),  # type: ignore[arg-type]
        onboarding_completed=True,
        onboarding_completed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_security_headers_present_on_health_and_api() -> None:
    app = create_app(Settings(app_env="test", rate_limit_enabled=False))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        live_res = await client.get("/health/live")
        meta_res = await client.get("/api/v1/meta")

    assert live_res.status_code == 200
    for resp in (live_res, meta_res):
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "camera=()" in resp.headers.get("Permissions-Policy", "")
        assert resp.headers.get("X-Request-ID")

    assert meta_res.headers.get("Cache-Control") == "no-store"


@pytest.mark.asyncio
async def test_rate_limiter_enforces_429_on_mutating_api_routes() -> None:
    app = create_app(
        Settings(
            app_env="test",
            rate_limit_enabled=True,
            api_write_rate_limit_per_minute=2,
            class_join_rate_limit_per_minute=1,
        )
    )
    app.dependency_overrides[get_current_user] = lambda: _fake_user("student")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.post("/api/v1/student/classes/join", json={"invitation_code": "AB"})
        r2 = await client.post("/api/v1/student/classes/join", json={"invitation_code": "CD"})

    # 1st attempt reaches validation/endpoint (422 for short code), 2nd is throttled at 429
    assert r1.status_code != 429
    assert r2.status_code == 429
    assert r2.json()["code"] == "RATE_LIMITED"
    assert int(r2.headers.get("Retry-After", "0")) >= 1


@pytest.mark.asyncio
async def test_payload_too_large_rejected_cleanly() -> None:
    app = create_app(
        Settings(
            app_env="test",
            rate_limit_enabled=False,
            max_request_body_bytes=64,
        )
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/v1/student/classes/join",
            content=b'{"invitation_code": "' + b"X" * 120 + b'"}',
            headers={"Content-Type": "application/json"},
        )

    assert res.status_code == 413
    assert res.json()["code"] == "PAYLOAD_TOO_LARGE"


@pytest.mark.asyncio
async def test_admin_operations_health_enforces_rbac_and_masks_secrets() -> None:
    app = create_app(Settings(app_env="test", rate_limit_enabled=False))

    class _FakeDbManager:
        async def check_health(self) -> bool:
            return True

    app.dependency_overrides[get_db_manager] = lambda: _FakeDbManager()

    # 1. Anonymous blocked (401)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        anon_res = await client.get("/api/v1/admin/operations/health")
    assert anon_res.status_code == 401

    # 2. Student blocked (403)
    app.dependency_overrides[get_current_user] = lambda: _fake_user("student")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        student_res = await client.get("/api/v1/admin/operations/health")
    assert student_res.status_code == 403

    # 3. Teacher blocked (403)
    app.dependency_overrides[get_current_user] = lambda: _fake_user("teacher")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        teacher_res = await client.get("/api/v1/admin/operations/health")
    assert teacher_res.status_code == 403

    # 4. Admin allowed (200) and zero secret values exposed
    app.dependency_overrides[get_current_user] = lambda: _fake_user("admin")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        admin_res = await client.get("/api/v1/admin/operations/health")
    assert admin_res.status_code == 200
    body = admin_res.json()
    assert body["overall_status"] in ("ok", "degraded")
    assert body["llm_provider_mode"] in ("live_llm", "deterministic_fallback")
    check_names = {c["name"] for c in body["checks"]}
    assert {"postgresql", "ml_classifier", "judge0", "socratic_llm"}.issubset(check_names)
    assert "api_key" not in admin_res.text.lower()
