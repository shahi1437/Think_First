import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.core.database import get_db_manager
from app.core.errors import AppError
from tests.conftest import StubDatabaseManager


async def test_health_live_returns_ok_and_request_id(async_client: AsyncClient) -> None:
    response = await async_client.get("/health/live")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "CodeMentor AI API"


async def test_health_ready_returns_200_when_database_healthy(
    test_app: FastAPI, async_client: AsyncClient
) -> None:
    test_app.dependency_overrides[get_db_manager] = lambda: StubDatabaseManager(healthy=True)
    try:
        response = await async_client.get("/health/ready")
    finally:
        test_app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


async def test_health_ready_returns_503_when_database_unavailable(
    test_app: FastAPI, async_client: AsyncClient
) -> None:
    test_app.dependency_overrides[get_db_manager] = lambda: StubDatabaseManager(healthy=False)
    try:
        response = await async_client.get("/health/ready")
    finally:
        test_app.dependency_overrides.clear()

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "unavailable"


async def test_api_v1_meta_echoes_valid_request_id(async_client: AsyncClient) -> None:
    custom_id = "req-phase1-check-001"
    response = await async_client.get("/api/v1/meta", headers={"X-Request-ID": custom_id})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["request_id"] == custom_id


async def test_api_v1_meta_replaces_invalid_request_id(async_client: AsyncClient) -> None:
    response = await async_client.get(
        "/api/v1/meta", headers={"X-Request-ID": "bad id with spaces!"}
    )

    assert response.status_code == 200
    generated_id = response.headers["X-Request-ID"]
    assert generated_id != "bad id with spaces!"
    assert response.json()["request_id"] == generated_id


async def test_app_error_returns_consistent_envelope(
    test_app: FastAPI, async_client: AsyncClient
) -> None:
    @test_app.get("/api/v1/_test-error")
    async def trigger_error() -> None:
        raise AppError(
            code="TEST_DOMAIN_ERROR",
            message="Controlled domain failure.",
            status_code=409,
            details={"field": "example"},
        )

    response = await async_client.get("/api/v1/_test-error")

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "TEST_DOMAIN_ERROR"
    assert body["message"] == "Controlled domain failure."
    assert body["details"] == {"field": "example"}
    assert body["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.parametrize("path", ["/api/v1/does-not-exist"])
async def test_not_found_uses_structured_error_format(async_client: AsyncClient, path: str) -> None:
    response = await async_client.get(path)
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "HTTP_404"
    assert "request_id" in body
