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
async def test_rate_limiter_ignores_all_spoofed_headers_from_untrusted_peer() -> None:
    app = create_app(
        Settings(
            app_env="test",
            rate_limit_enabled=True,
            class_join_rate_limit_per_minute=1,
            trusted_proxy_cidrs=[],
        )
    )
    app.dependency_overrides[get_current_user] = lambda: _fake_user("student")

    transport = ASGITransport(app=app, client=("198.51.100.5", 50000))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post(
            "/api/v1/student/classes/join",
            json={"invitation_code": "AB"},
            headers={
                "CF-Connecting-IP": "203.0.113.1",
                "True-Client-IP": "203.0.113.2",
                "X-Real-IP": "203.0.113.3",
                "X-Forwarded-For": "203.0.113.4",
            },
        )
        # Rotating every forwarding header from an untrusted direct peer MUST NOT bypass limit
        r2 = await client.post(
            "/api/v1/student/classes/join",
            json={"invitation_code": "CD"},
            headers={"CF-Connecting-IP": "203.0.113.99"},
        )
        r3 = await client.post(
            "/api/v1/student/classes/join",
            json={"invitation_code": "EF"},
            headers={"True-Client-IP": "203.0.113.98"},
        )
        r4 = await client.post(
            "/api/v1/student/classes/join",
            json={"invitation_code": "GH"},
            headers={"X-Forwarded-For": "203.0.113.97"},
        )

    assert r1.status_code != 429
    for blocked in (r2, r3, r4):
        assert blocked.status_code == 429
        assert blocked.json()["code"] == "RATE_LIMITED"


@pytest.mark.asyncio
async def test_rate_limiter_single_trusted_proxy_resists_spoofing_and_separates_users() -> None:
    app = create_app(
        Settings(
            app_env="test",
            rate_limit_enabled=True,
            class_join_rate_limit_per_minute=1,
            trusted_proxy_cidrs=["10.0.0.0/8"],
            trusted_proxy_hops=1,
        )
    )
    app.dependency_overrides[get_current_user] = lambda: _fake_user("student")

    transport = ASGITransport(app=app, client=("10.0.0.5", 443))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A sends spoofed leftmost XFF and spoofed CF-Connecting-IP / True-Client-IP
        r1 = await client.post(
            "/api/v1/student/classes/join",
            json={"invitation_code": "AB"},
            headers={
                "CF-Connecting-IP": "198.51.100.1",
                "True-Client-IP": "198.51.100.2",
                "X-Forwarded-For": "198.51.100.10, 203.0.113.77",
            },
        )
        # Same User A rotates spoofed CF/True-Client-IP & leftmost XFF -> still 203.0.113.77
        r2 = await client.post(
            "/api/v1/student/classes/join",
            json={"invitation_code": "CD"},
            headers={
                "CF-Connecting-IP": "198.51.100.55",
                "True-Client-IP": "198.51.100.56",
                "X-Forwarded-For": "198.51.100.99, 203.0.113.77",
            },
        )
        # Distinct User B behind the same trusted proxy is NOT collaterally throttled
        r_user_b = await client.post(
            "/api/v1/student/classes/join",
            json={"invitation_code": "EF"},
            headers={"X-Forwarded-For": "203.0.113.88"},
        )

    assert r1.status_code != 429
    assert r2.status_code == 429
    assert r2.json()["code"] == "RATE_LIMITED"
    assert r_user_b.status_code != 429


@pytest.mark.asyncio
async def test_rate_limiter_multihop_proxy_chain_separates_users_and_blocks_spoofing() -> None:
    app = create_app(
        Settings(
            app_env="test",
            rate_limit_enabled=True,
            class_join_rate_limit_per_minute=1,
            trusted_proxy_cidrs=["10.0.0.0/8", "172.68.0.0/16"],
            trusted_proxy_hops=2,
        )
    )
    app.dependency_overrides[get_current_user] = lambda: _fake_user("student")

    # Direct peer is Render proxy (10.0.0.5); Cloudflare edge (172.68.1.1) is the rightmost XFF hop
    transport = ASGITransport(app=app, client=("10.0.0.5", 443))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        u1_first = await client.post(
            "/api/v1/student/classes/join",
            json={"invitation_code": "AB"},
            headers={"X-Forwarded-For": "198.51.100.1, 203.0.113.10, 172.68.1.1"},
        )
        # Distinct user behind same Cloudflare+Render chain must NOT be collaterally throttled
        u2_first = await client.post(
            "/api/v1/student/classes/join",
            json={"invitation_code": "CD"},
            headers={"X-Forwarded-For": "203.0.113.20, 172.68.1.1"},
        )
        # User 1 rotating spoofed leftmost XFF (including fake Cloudflare hop) is still throttled
        u1_spoof = await client.post(
            "/api/v1/student/classes/join",
            json={"invitation_code": "EF"},
            headers={"X-Forwarded-For": "198.51.100.9, 172.68.9.9, 203.0.113.10, 172.68.1.1"},
        )

    assert u1_first.status_code != 429
    assert u2_first.status_code != 429
    assert u1_spoof.status_code == 429
    assert u1_spoof.json()["code"] == "RATE_LIMITED"


@pytest.mark.asyncio
async def test_rate_limiter_explicit_edge_header_requires_trusted_peer() -> None:
    app = create_app(
        Settings(
            app_env="test",
            rate_limit_enabled=True,
            class_join_rate_limit_per_minute=1,
            trusted_proxy_cidrs=["10.0.0.0/8"],
            trusted_proxy_client_ip_header="CF-Connecting-IP",
        )
    )
    app.dependency_overrides[get_current_user] = lambda: _fake_user("student")

    # Trusted proxy peer: configured CF-Connecting-IP header is honored
    trusted_transport = ASGITransport(app=app, client=("10.0.0.9", 443))
    async with AsyncClient(transport=trusted_transport, base_url="http://test") as client:
        t1 = await client.post(
            "/api/v1/student/classes/join",
            json={"invitation_code": "AB"},
            headers={"CF-Connecting-IP": "203.0.113.31"},
        )
        t2 = await client.post(
            "/api/v1/student/classes/join",
            json={"invitation_code": "CD"},
            headers={"CF-Connecting-IP": "203.0.113.32"},
        )
        t3 = await client.post(
            "/api/v1/student/classes/join",
            json={"invitation_code": "EF"},
            headers={"CF-Connecting-IP": "203.0.113.31"},
        )

    assert t1.status_code != 429
    assert t2.status_code != 429
    assert t3.status_code == 429

    # Untrusted peer: CF-Connecting-IP is STILL ignored even when configured
    untrusted_transport = ASGITransport(app=app, client=("198.51.100.44", 51000))
    async with AsyncClient(transport=untrusted_transport, base_url="http://test") as client:
        u1 = await client.post(
            "/api/v1/student/classes/join",
            json={"invitation_code": "AB"},
            headers={"CF-Connecting-IP": "203.0.113.41"},
        )
        u2 = await client.post(
            "/api/v1/student/classes/join",
            json={"invitation_code": "CD"},
            headers={"CF-Connecting-IP": "203.0.113.42"},
        )

    assert u1.status_code != 429
    assert u2.status_code == 429


def test_trusted_proxy_settings_validation_rejects_invalid_cidr_or_header() -> None:
    s = Settings(
        app_env="test",
        trusted_proxy_cidrs="10.0.0.0/8, 172.68.0.0/16",
        trusted_proxy_hops=2,
        trusted_proxy_client_ip_header="CF-Connecting-IP",
    )
    assert s.trusted_proxy_cidrs == ["10.0.0.0/8", "172.68.0.0/16"]
    assert len(s.parsed_trusted_proxy_networks()) == 2

    with pytest.raises(ValueError):
        Settings(app_env="test", trusted_proxy_cidrs=["not-a-cidr"])

    with pytest.raises(ValueError):
        Settings(app_env="test", trusted_proxy_client_ip_header="X-Arbitrary-Header")


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
