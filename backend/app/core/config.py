import json
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip().rstrip("/") for item in parsed if str(item).strip()]
            return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip().rstrip("/") for item in value if str(item).strip()]
        raise ValueError("CORS_ORIGINS must be a JSON array or comma-separated list of origins.")

    database_url: str = "postgresql+asyncpg://codementor:codementor_dev@localhost:5432/codementor"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_health_timeout_seconds: float = 5.0

    # Phase 2+ Supabase settings (validated when auth endpoints are enabled)
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    jwks_cache_ttl_seconds: int = 3600
    jwks_fetch_timeout_seconds: float = 5.0

    # Phase 3+ Judge0 CE isolated code execution settings
    judge0_base_url: str = "http://127.0.0.1:2359"
    judge0_auth_mode: str = "auto"  # "auto" | "auth_token" | "rapidapi" | "disabled"
    judge0_auth_token: str | None = None
    judge0_rapidapi_key: str | None = None
    judge0_rapidapi_host: str = "judge0-ce.p.rapidapi.com"
    judge0_http_timeout_seconds: float = 15.0
    judge0_poll_interval_seconds: float = 0.4
    judge0_poll_timeout_seconds: float = 20.0
    judge0_max_retries: int = 2
    # Phase 3+ Self-hosted Piston secure fallback execution settings
    execution_fallback_enabled: bool = True
    piston_enabled: bool = True
    piston_base_url: str = "http://127.0.0.1:2000"
    piston_http_timeout_seconds: float = 15.0
    piston_compile_timeout_ms: int = 10000
    piston_run_timeout_ms: int = 3000
    piston_max_output_bytes: int = 65536
    max_source_code_bytes: int = 65536
    execution_rate_limit_per_minute: int = 20
    execution_daily_quota: int = 200

    # Phase 4+ ML, RAG & Socratic AI Mentor settings
    ml_model_artifact_path: str = "../ml/artifacts/error_classifier_v1.joblib"
    ml_low_confidence_threshold: float = 0.55
    rag_embedding_dimensions: int = 256
    rag_similarity_threshold: float = 0.22
    llm_provider: Literal["none", "openai", "gemini", "ollama"] = "none"
    llm_model: str = ""
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_timeout_seconds: float = 30.0
    mentor_rate_limit_per_minute: int = 15

    # Phase 9 security & observability settings
    rate_limit_enabled: bool = True
    api_write_rate_limit_per_minute: int = 120
    class_join_rate_limit_per_minute: int = 15
    portal_verify_rate_limit_per_minute: int = 20
    max_request_body_bytes: int = 2_097_152
    slow_request_threshold_ms: float = 2500.0

    def validate_production_readiness(self) -> list[str]:
        """Return configuration gap keys in production without exposing secret values."""
        issues: list[str] = []
        if self.app_env != "production":
            return issues

        db_lower = self.database_url.lower()
        if "localhost" in db_lower or "127.0.0.1" in db_lower or "codementor_dev" in db_lower:
            issues.append("DATABASE_URL points to local or dev defaults")

        supa = (self.supabase_url or "").strip().lower()
        if not supa or "127.0.0.1" in supa or "localhost" in supa or "your-project-ref" in supa:
            issues.append("SUPABASE_URL missing or points to local/placeholder host")

        if any(
            origin.strip() == "*" or "localhost" in origin.lower() or "127.0.0.1" in origin.lower()
            for origin in self.cors_origins
        ):
            issues.append("CORS_ORIGINS allows wildcard or localhost in production")

        j0 = self.judge0_base_url.strip().lower()
        j0_mode = (self.judge0_auth_mode or "auto").strip().lower()
        if j0_mode == "disabled":
            issues.append("JUDGE0_AUTH_MODE is disabled (code execution unavailable)")
        elif j0_mode not in {"auto", "auth_token", "rapidapi"}:
            issues.append("JUDGE0_AUTH_MODE must be one of: auto, auth_token, rapidapi, disabled")
        else:
            if not j0 or "127.0.0.1" in j0 or "localhost" in j0:
                issues.append("JUDGE0_BASE_URL points to local loopback in production")
            if j0_mode == "rapidapi" or (j0_mode == "auto" and "rapidapi.com" in j0):
                if not (self.judge0_rapidapi_key or "").strip():
                    issues.append("JUDGE0_RAPIDAPI_KEY is missing for RapidAPI Judge0 mode")
                if j0 and not j0.startswith("https://"):
                    issues.append("JUDGE0_BASE_URL must use HTTPS for RapidAPI Judge0 mode")

        return issues


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
