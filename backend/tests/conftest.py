from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


class StubDatabaseManager:
    """Test double for verifying readiness probe behavior deterministically."""

    def __init__(self, healthy: bool) -> None:
        self._healthy = healthy

    async def check_health(self) -> bool:
        return self._healthy

    async def dispose(self) -> None:
        return None


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        app_env="test",
        app_name="CodeMentor AI API",
        app_version="0.1.0-test",
        cors_origins=["http://localhost:3000"],
    )


@pytest.fixture
def test_app(test_settings: Settings) -> FastAPI:
    return create_app(settings=test_settings)


@pytest.fixture
async def async_client(test_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
