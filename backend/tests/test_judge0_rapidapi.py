"""Automated tests for dual-mode Judge0 authentication (Self-hosted + RapidAPI Option B)."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from httpx import ASGITransport

from app.core.config import Settings, get_settings
from app.core.database import get_db_manager
from app.core.errors import AppError
from app.integrations.judge0.client import (
    HttpJudge0Client,
    build_judge0_auth_headers,
    resolve_judge0_auth_mode,
)
from app.main import create_app
from app.repositories.identity import UserRecord


def _b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def test_resolve_auth_headers_self_hosted_and_rapidapi_modes() -> None:
    self_hosted = Settings(
        judge0_base_url="http://127.0.0.1:2359",
        judge0_auth_token="local-token-xyz",
    )
    assert resolve_judge0_auth_mode(self_hosted) == "auth_token"
    assert build_judge0_auth_headers(self_hosted) == {"X-Auth-Token": "local-token-xyz"}

    no_token_local = Settings(judge0_base_url="http://127.0.0.1:2359")
    assert resolve_judge0_auth_mode(no_token_local) == "auth_token"
    assert build_judge0_auth_headers(no_token_local) == {}

    rapid_auto = Settings(
        judge0_base_url="https://judge0-ce.p.rapidapi.com",
        judge0_rapidapi_key="rapid-secret-demo-key",
    )
    assert resolve_judge0_auth_mode(rapid_auto) == "rapidapi"
    assert build_judge0_auth_headers(rapid_auto) == {
        "X-RapidAPI-Key": "rapid-secret-demo-key",
        "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
    }

    rapid_inferred_host = Settings(
        judge0_base_url="https://custom-judge0.p.rapidapi.com",
        judge0_auth_mode="rapidapi",
        judge0_rapidapi_key="rapid-secret-demo-key",
        judge0_rapidapi_host="",
    )
    assert build_judge0_auth_headers(rapid_inferred_host) == {
        "X-RapidAPI-Key": "rapid-secret-demo-key",
        "X-RapidAPI-Host": "custom-judge0.p.rapidapi.com",
    }

    missing_rapid_key = Settings(
        judge0_base_url="https://judge0-ce.p.rapidapi.com",
        judge0_auth_mode="rapidapi",
        judge0_rapidapi_key="",
    )
    with pytest.raises(AppError) as exc_info:
        build_judge0_auth_headers(missing_rapid_key)
    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "EXECUTION_SERVICE_UNAVAILABLE"

    invalid_mode = Settings(judge0_auth_mode="oauth2")
    with pytest.raises(AppError) as invalid_exc:
        resolve_judge0_auth_mode(invalid_mode)
    assert invalid_exc.value.status_code == 500


def test_production_readiness_validates_rapidapi_configuration() -> None:
    missing_key = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://postgres:secret@db.example.supabase.co:5432/postgres",
        supabase_url="https://exampleproject.supabase.co",
        cors_origins=["https://think-first-pi.vercel.app"],
        judge0_base_url="https://judge0-ce.p.rapidapi.com",
        judge0_auth_mode="auto",
        judge0_rapidapi_key=None,
    )
    warnings = missing_key.validate_production_readiness()
    assert any("JUDGE0_RAPIDAPI_KEY" in item for item in warnings)

    insecure_scheme = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://postgres:secret@db.example.supabase.co:5432/postgres",
        supabase_url="https://exampleproject.supabase.co",
        cors_origins=["https://think-first-pi.vercel.app"],
        judge0_base_url="http://judge0-ce.p.rapidapi.com",
        judge0_auth_mode="rapidapi",
        judge0_rapidapi_key="demo-key-value",
    )
    http_warnings = insecure_scheme.validate_production_readiness()
    assert any("HTTPS" in item for item in http_warnings)

    valid_rapidapi = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://postgres:secret@db.example.supabase.co:5432/postgres",
        supabase_url="https://exampleproject.supabase.co",
        cors_origins=["https://think-first-pi.vercel.app"],
        judge0_base_url="https://judge0-ce.p.rapidapi.com",
        judge0_auth_mode="rapidapi",
        judge0_rapidapi_key="demo-key-value",
        judge0_rapidapi_host="judge0-ce.p.rapidapi.com",
    )
    assert valid_rapidapi.validate_production_readiness() == []


async def test_http_judge0_client_executes_with_self_hosted_and_rapidapi_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_headers: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.append(dict(request.headers))
        if request.method == "GET" and request.url.path == "/languages":
            return httpx.Response(200, json=[{"id": 71, "name": "Python (3.8.1)"}])
        if request.method == "POST" and request.url.path == "/submissions":
            return httpx.Response(201, json={"token": "tok-rapid-123"})
        if request.method == "GET" and request.url.path == "/submissions/tok-rapid-123":
            return httpx.Response(
                200,
                json={
                    "token": "tok-rapid-123",
                    "status": {"id": 3, "description": "Accepted"},
                    "stdout": _b64("42\n"),
                    "stderr": None,
                    "compile_output": None,
                    "time": "0.014",
                    "memory": 3100,
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def mock_client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx, "AsyncClient", mock_client)

    rapid_settings = Settings(
        judge0_base_url="https://judge0-ce.p.rapidapi.com",
        judge0_auth_mode="rapidapi",
        judge0_rapidapi_key="super-secret-rapidapi-key",
        judge0_rapidapi_host="judge0-ce.p.rapidapi.com",
        judge0_auth_token="should-not-be-sent",
        judge0_poll_interval_seconds=0.1,
    )
    client = HttpJudge0Client(rapid_settings)

    langs = await client.list_languages()
    assert len(langs) == 1 and langs[0].id == 71

    outcome = await client.execute_test_case(
        source_code="print(42)",
        judge0_language_id=71,
        stdin="",
        expected_output="42",
        cpu_time_limit_seconds=2.0,
        memory_limit_kb=131072,
    )
    assert outcome.verdict == "accepted"
    assert outcome.stdout == "42\n"
    assert len(captured_headers) == 3
    for hdrs in captured_headers:
        assert hdrs.get("x-rapidapi-key") == "super-secret-rapidapi-key"
        assert hdrs.get("x-rapidapi-host") == "judge0-ce.p.rapidapi.com"
        assert "x-auth-token" not in hdrs

    captured_headers.clear()
    self_settings = Settings(
        judge0_base_url="http://127.0.0.1:2359",
        judge0_auth_mode="auth_token",
        judge0_auth_token="local-auth-token-999",
        judge0_rapidapi_key="ignored-in-auth-token-mode",
        judge0_poll_interval_seconds=0.1,
    )
    self_client = HttpJudge0Client(self_settings)
    outcome_local = await self_client.execute_test_case(
        source_code="print(42)",
        judge0_language_id=71,
        stdin="",
        expected_output="42",
        cpu_time_limit_seconds=2.0,
        memory_limit_kb=131072,
    )
    assert outcome_local.verdict == "accepted"
    for hdrs in captured_headers:
        assert hdrs.get("x-auth-token") == "local-auth-token-999"
        assert "x-rapidapi-key" not in hdrs


@pytest.mark.parametrize(
    ("status_code", "expected_http", "expected_code"),
    [
        (429, 429, "EXECUTION_RATE_LIMITED"),
        (401, 503, "EXECUTION_SERVICE_UNAVAILABLE"),
        (403, 503, "EXECUTION_SERVICE_UNAVAILABLE"),
    ],
)
async def test_http_judge0_client_handles_rapidapi_quota_and_auth_failures_without_leaking_keys(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    expected_http: int,
    expected_code: str,
) -> None:
    calls = 0
    secret_key = "rapid-secret-never-leak-token"

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            status_code,
            text=json.dumps({"message": f"Upstream failed with key={secret_key}"}),
        )

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def mock_client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx, "AsyncClient", mock_client)

    settings = Settings(
        judge0_base_url="https://judge0-ce.p.rapidapi.com",
        judge0_auth_mode="rapidapi",
        judge0_rapidapi_key=secret_key,
        judge0_max_retries=2,
    )
    client = HttpJudge0Client(settings)

    with pytest.raises(AppError) as exc_info:
        await client.list_languages()

    assert calls == 1  # Never retry 401/403/429 quota or auth errors
    assert exc_info.value.status_code == expected_http
    assert exc_info.value.code == expected_code
    assert secret_key not in exc_info.value.message


async def test_admin_health_uses_rapidapi_headers_and_backend_boots_without_judge0(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.v1.deps import get_current_user

    seen_about_headers: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/about":
            seen_about_headers.append(dict(request.headers))
            return httpx.Response(200, json={"version": "1.13.1-rapid"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def mock_client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        if "transport" not in kwargs and (
            "base_url" not in kwargs or str(kwargs.get("base_url", "")).startswith("http://test")
        ):
            kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx, "AsyncClient", mock_client)

    secret_key = "rapid-health-secret-value"
    settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://postgres:secret@db.example.supabase.co:5432/postgres",
        supabase_url="https://exampleproject.supabase.co",
        cors_origins=["https://think-first-pi.vercel.app"],
        judge0_base_url="https://judge0-ce.p.rapidapi.com",
        judge0_auth_mode="rapidapi",
        judge0_rapidapi_key=secret_key,
    )
    app = create_app(settings=settings)

    class _FakeDbManager:
        async def check_health(self) -> bool:
            return True

    admin_user = UserRecord(
        id=uuid4(),
        email="admin@thinkfirst.edu",
        full_name="Admin User",
        avatar_url=None,
        roles=["admin"],
        onboarding_completed=True,
        onboarding_completed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db_manager] = lambda: _FakeDbManager()
    app.dependency_overrides[get_current_user] = lambda: admin_user

    # Use explicit ASGITransport directly with real_async_client to avoid monkeypatch recursion
    async with real_async_client(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as api_client:
        live_res = await api_client.get("/health/live")
        ready_res = await api_client.get("/health/ready")
        ops_res = await api_client.get("/api/v1/admin/operations/health")

    assert live_res.status_code == 200
    assert ready_res.status_code == 200
    assert ops_res.status_code == 200

    assert len(seen_about_headers) == 1
    assert seen_about_headers[0].get("x-rapidapi-key") == secret_key
    assert seen_about_headers[0].get("x-rapidapi-host") == "judge0-ce.p.rapidapi.com"
    assert secret_key not in ops_res.text

    checks = {c["name"]: c for c in ops_res.json()["checks"]}
    assert checks["judge0"]["status"] == "ok"
    assert "1.13.1-rapid" in checks["judge0"]["detail"]

    # Backend also remains deployable/ready when RapidAPI key is not yet set
    unconfigured_settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://postgres:secret@db.example.supabase.co:5432/postgres",
        supabase_url="https://exampleproject.supabase.co",
        cors_origins=["https://think-first-pi.vercel.app"],
        judge0_base_url="https://judge0-ce.p.rapidapi.com",
        judge0_auth_mode="rapidapi",
        judge0_rapidapi_key="",
    )
    app.dependency_overrides[get_settings] = lambda: unconfigured_settings
    async with real_async_client(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as api_client:
        ready_without_j0 = await api_client.get("/health/ready")
        ops_without_j0 = await api_client.get("/api/v1/admin/operations/health")

    assert ready_without_j0.status_code == 200
    assert ops_without_j0.status_code == 200
    checks_unconfigured = {c["name"]: c for c in ops_without_j0.json()["checks"]}
    assert checks_unconfigured["judge0"]["status"] == "unavailable"
    assert "not configured" in checks_unconfigured["judge0"]["detail"]


async def test_judge0_disabled_and_empty_url_fail_closed_with_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.integrations.judge0.client import is_judge0_configured

    network_calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal network_calls
        network_calls += 1
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def mock_client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx, "AsyncClient", mock_client)

    for disabled_settings in (
        Settings(
            app_env="production",
            database_url="postgresql+asyncpg://postgres.ref:pw@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres",
            supabase_url="https://vsmrwfoqqjvomtjpypyv.supabase.co",
            cors_origins=["https://think-first-pi.vercel.app"],
            judge0_auth_mode="disabled",
            judge0_base_url="",
        ),
        Settings(
            app_env="production",
            database_url="postgresql+asyncpg://postgres.ref:pw@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres",
            supabase_url="https://vsmrwfoqqjvomtjpypyv.supabase.co",
            cors_origins=["https://think-first-pi.vercel.app"],
            judge0_auth_mode="auto",
            judge0_base_url="",
        ),
    ):
        assert is_judge0_configured(disabled_settings) is False
        client = HttpJudge0Client(disabled_settings)
        with pytest.raises(AppError) as lang_err:
            await client.list_languages()
        assert lang_err.value.status_code == 503
        assert lang_err.value.code == "EXECUTION_SERVICE_UNAVAILABLE"

        with pytest.raises(AppError) as exec_err:
            await client.execute_test_case(
                source_code="print(1)",
                judge0_language_id=71,
                stdin="",
                expected_output="1",
                cpu_time_limit_seconds=1.0,
                memory_limit_kb=65536,
            )
        assert exec_err.value.status_code == 503
        assert exec_err.value.code == "EXECUTION_SERVICE_UNAVAILABLE"

    assert network_calls == 0

    disabled_prod = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://postgres.ref:pw@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres",
        supabase_url="https://vsmrwfoqqjvomtjpypyv.supabase.co",
        cors_origins=["https://think-first-pi.vercel.app"],
        judge0_auth_mode="disabled",
    )
    warnings = disabled_prod.validate_production_readiness()
    assert warnings == ["JUDGE0_AUTH_MODE is disabled (code execution unavailable)"]


def test_database_url_normalization_and_cors_env_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.database import normalize_database_url_and_connect_args

    session_url, session_args = normalize_database_url_and_connect_args(
        "postgresql://postgres.vsmrwfoqqjvomtjpypyv:myPass@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=require"
    )
    assert session_url == (
        "postgresql+asyncpg://postgres.vsmrwfoqqjvomtjpypyv:myPass@"
        "aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"
    )
    assert session_args == {"ssl": "require"}

    tx_url, tx_args = normalize_database_url_and_connect_args(
        "postgres://postgres.vsmrwfoqqjvomtjpypyv:myPass@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?pgbouncer=true"
    )
    assert tx_url == (
        "postgresql+asyncpg://postgres.vsmrwfoqqjvomtjpypyv:myPass@"
        "aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
    )
    assert tx_args == {"ssl": "require", "statement_cache_size": 0}

    local_url, local_args = normalize_database_url_and_connect_args(
        "postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres"
    )
    assert local_url == "postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres"
    assert local_args == {}

    monkeypatch.setenv("CORS_ORIGINS", "https://think-first-pi.vercel.app/")
    single_cors = Settings(_env_file=None)  # type: ignore[call-arg]
    assert single_cors.cors_origins == ["https://think-first-pi.vercel.app"]

    monkeypatch.setenv(
        "CORS_ORIGINS",
        '["https://think-first-pi.vercel.app/", "https://think-first-staysafe.vercel.app"]',
    )
    json_cors = Settings(_env_file=None)  # type: ignore[call-arg]
    assert json_cors.cors_origins == [
        "https://think-first-pi.vercel.app",
        "https://think-first-staysafe.vercel.app",
    ]


async def test_execution_service_fails_before_db_write_when_judge0_disabled() -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    from app.schemas.problems import SubmissionCreateRequest
    from app.services.execution.service import ExecutionService

    disabled_settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://u:p@pooler.supabase.com:5432/postgres",
        supabase_url="https://vsmrwfoqqjvomtjpypyv.supabase.co",
        cors_origins=["https://think-first-pi.vercel.app"],
        judge0_auth_mode="disabled",
    )
    repo = MagicMock()
    repo.get_quota_counts = AsyncMock(return_value=(0, 0))
    problem_id = uuid4()
    repo.get_published_problem = AsyncMock(
        return_value=(
            SimpleNamespace(id=problem_id),
            SimpleNamespace(
                id=uuid4(),
                mode="coding",
                variants=[SimpleNamespace(language_slug="python")],
                test_cases=[SimpleNamespace(id=uuid4(), ordinal=1, is_hidden=False)],
            ),
        )
    )
    repo.get_language_by_slug = AsyncMock(
        return_value=SimpleNamespace(slug="python", is_enabled=True, judge0_language_id=71)
    )
    repo.create_submission = AsyncMock()

    service = ExecutionService(
        repository=repo,
        judge0=HttpJudge0Client(disabled_settings),
        settings=disabled_settings,
    )
    user = UserRecord(
        id=uuid4(),
        email="student@thinkfirst.edu",
        full_name="Student User",
        avatar_url=None,
        roles=["student"],
        onboarding_completed=True,
        onboarding_completed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )

    with pytest.raises(AppError) as exc_info:
        await service.execute_submission(
            user=user,
            payload=SubmissionCreateRequest(
                problem_id=problem_id,
                language_slug="python",
                submission_kind="submit",
                source_code="print(1)",
            ),
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "EXECUTION_SERVICE_UNAVAILABLE"
    repo.create_submission.assert_not_awaited()
