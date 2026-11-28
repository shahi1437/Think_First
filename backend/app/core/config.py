import ipaddress
import json
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network
_ALLOWED_PROXY_IP_HEADERS = frozenset({"cf-connecting-ip", "true-client-ip", "x-real-ip"})


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
    db_pool_size: int = 12
    db_max_overflow: int = 15
    db_health_timeout_seconds: float = 5.0

    # Phase 2+ Supabase settings (validated when auth endpoints are enabled)
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    jwks_cache_ttl_seconds: int = 3600
    jwks_fetch_timeout_seconds: float = 5.0

    # Phase 3+ Judge0 CE isolated code execution settings
    judge0_base_url: str = "http://127.0.0.1:2359"
    # Supported modes: "auto" | "auth_token" | "rapidapi" | "worker_queue" | "disabled"
    judge0_auth_mode: str = "auto"
    judge0_auth_token: str | None = None
    judge0_rapidapi_key: str | None = None
    judge0_rapidapi_host: str = "judge0-ce.p.rapidapi.com"
    judge0_http_timeout_seconds: float = 15.0
    judge0_poll_interval_seconds: float = 0.4
    judge0_poll_timeout_seconds: float = 20.0
    judge0_max_retries: int = 2
    # Outbound & embedded execution worker queue settings (`judge0_auth_mode == "worker_queue"`)
    execution_worker_token: str | None = None
    execution_worker_heartbeat_ttl_seconds: int = 35
    execution_job_ttl_seconds: int = 90
    execution_job_lease_seconds: int = 45
    execution_max_concurrent_jobs_per_user: int = 2
    execution_max_queue_depth: int = 25
    execution_sync_wait_timeout_seconds: float = 35.0
    execution_embedded_worker_enabled: bool = True
    execution_embedded_judge0_base_url: str = "https://ce.judge0.com"
    execution_embedded_worker_concurrency: int = Field(default=1, ge=1, le=2)
    execution_embedded_worker_poll_seconds: float = Field(default=15.0, ge=1.0, le=30.0)
    execution_embedded_worker_heartbeat_seconds: float = Field(default=15.0, ge=5.0, le=25.0)
    execution_allowed_emails: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("execution_allowed_emails", mode="before")
    @classmethod
    def _parse_execution_allowed_emails(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip().lower() for item in parsed if str(item).strip()]
            return [item.strip().lower() for item in raw.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip().lower() for item in value if str(item).strip()]
        raise ValueError("EXECUTION_ALLOWED_EMAILS must be a JSON array or comma-separated emails.")

    # Phase 3+ Self-hosted Piston secure fallback execution settings
    execution_fallback_enabled: bool = True
    piston_enabled: bool = True
    piston_base_url: str = "http://127.0.0.1:2000"
    piston_isolated_host_verified: bool = False
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
    trusted_proxy_cidrs: Annotated[list[str], NoDecode] = Field(default_factory=list)
    trusted_proxy_hops: int = Field(default=1, ge=1, le=10)
    trusted_proxy_client_ip_header: str | None = None
    max_request_body_bytes: int = 2_097_152
    slow_request_threshold_ms: float = 2500.0

    @field_validator("trusted_proxy_cidrs", mode="before")
    @classmethod
    def _parse_trusted_proxy_cidrs(cls, value: object) -> list[str]:
        if value is None:
            return []
        items: list[str]
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    raise ValueError(
                        "TRUSTED_PROXY_CIDRS must be a JSON array or comma-separated list of CIDRs."
                    )
                items = [str(item).strip() for item in parsed if str(item).strip()]
            else:
                items = [item.strip() for item in raw.split(",") if item.strip()]
        elif isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
        else:
            raise ValueError(
                "TRUSTED_PROXY_CIDRS must be a JSON array or comma-separated list of CIDRs."
            )
        return [str(ipaddress.ip_network(cidr, strict=False)) for cidr in items]

    @field_validator("trusted_proxy_client_ip_header", mode="before")
    @classmethod
    def _validate_trusted_proxy_client_ip_header(cls, value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        if cleaned.lower() not in _ALLOWED_PROXY_IP_HEADERS:
            allowed = ", ".join(sorted(_ALLOWED_PROXY_IP_HEADERS))
            raise ValueError(f"TRUSTED_PROXY_CLIENT_IP_HEADER must be one of: {allowed}")
        return cleaned

    def parsed_trusted_proxy_networks(self) -> tuple[IPNetwork, ...]:
        """Return parsed trusted reverse-proxy CIDR networks."""
        return tuple(ipaddress.ip_network(cidr, strict=False) for cidr in self.trusted_proxy_cidrs)

    @model_validator(mode="after")
    def _enforce_production_piston_default(self) -> "Settings":
        """Keep Piston fallback secure-by-default (disabled) in production unless explicitly set."""
        if self.app_env == "production" and "piston_enabled" not in self.model_fields_set:
            self.piston_enabled = False
        return self

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
        elif j0_mode == "worker_queue":
            if len((self.execution_worker_token or "").strip()) < 24:
                issues.append(
                    "EXECUTION_WORKER_TOKEN is missing or too short (<24 chars) "
                    "for worker_queue mode"
                )
            if self.execution_embedded_worker_enabled:
                emb_url = self.execution_embedded_judge0_base_url.strip().lower()
                if (
                    not emb_url
                    or not emb_url.startswith("https://")
                    or "127.0.0.1" in emb_url
                    or "localhost" in emb_url
                ):
                    issues.append(
                        "EXECUTION_EMBEDDED_JUDGE0_BASE_URL must be a non-loopback HTTPS URL "
                        "in production when embedded worker is enabled"
                    )
        elif j0_mode not in {"auto", "auth_token", "rapidapi"}:
            issues.append(
                "JUDGE0_AUTH_MODE must be one of: auto, auth_token, rapidapi, "
                "worker_queue, disabled"
            )
        else:
            if not j0 or "127.0.0.1" in j0 or "localhost" in j0:
                issues.append("JUDGE0_BASE_URL points to local loopback in production")
            if j0_mode == "rapidapi" or (j0_mode == "auto" and "rapidapi.com" in j0):
                if not (self.judge0_rapidapi_key or "").strip():
                    issues.append("JUDGE0_RAPIDAPI_KEY is missing for RapidAPI Judge0 mode")
                if j0 and not j0.startswith("https://"):
                    issues.append("JUDGE0_BASE_URL must use HTTPS for RapidAPI Judge0 mode")

        if self.execution_fallback_enabled and self.piston_enabled:
            piston_url = self.piston_base_url.strip().lower()
            if not piston_url or "127.0.0.1" in piston_url or "localhost" in piston_url:
                issues.append(
                    "PISTON_BASE_URL points to local loopback in production; disable Piston "
                    "(PISTON_ENABLED=false) or host Piston on a dedicated isolated VM"
                )
            if not self.piston_isolated_host_verified:
                issues.append(
                    "Piston fallback requires dedicated VM/microVM isolation in production "
                    "(disable PISTON_ENABLED or set PISTON_ISOLATED_HOST_VERIFIED=true)"
                )

        return issues


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
