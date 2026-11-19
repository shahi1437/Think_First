from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "CodeMentor AI API"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    database_url: str = "postgresql+asyncpg://codementor:codementor_dev@localhost:5432/codementor"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_health_timeout_seconds: float = 2.0

    # Phase 2+ Supabase settings (validated when auth endpoints are enabled)
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    jwks_cache_ttl_seconds: int = 3600
    jwks_fetch_timeout_seconds: float = 5.0


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
