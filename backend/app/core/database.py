import asyncio
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _extract_safe_db_error_context(exc: Exception) -> dict[str, Any]:
    """Return non-sensitive DB error telemetry (class, SQLSTATE, safe hint; zero secrets)."""
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(exc, "sqlstate", None)
    orig_type = type(orig).__name__ if orig is not None else type(exc).__name__
    msg_lower = f"{type(exc).__name__} {orig_type} {orig or exc}".lower()

    hint = "unknown"
    if "tenant" in msg_lower or "enotfound" in msg_lower:
        hint = "tenant_or_user_not_found"
    elif "circuit breaker" in msg_lower:
        hint = "circuit_breaker_open"
    elif sqlstate == "28P01" or "password" in msg_lower or "authentication failed" in msg_lower:
        hint = "authentication_failed"
    elif "ssl" in msg_lower or "certificate" in msg_lower:
        hint = "ssl_or_tls_error"
    elif isinstance(exc, TimeoutError) or "timeout" in msg_lower:
        hint = "timeout"
    elif "network is unreachable" in msg_lower or "name or service not known" in msg_lower:
        hint = "network_or_dns_error"
    elif "closed" in msg_lower or "connectiondoesnotexist" in msg_lower or "reset" in msg_lower:
        hint = "connection_closed"

    return {
        "error_type": type(exc).__name__,
        "orig_type": orig_type,
        "sqlstate": str(sqlstate) if sqlstate else None,
        "hint": hint,
    }


def normalize_database_url_and_connect_args(raw_url: str) -> tuple[str, dict[str, Any]]:
    """Normalize PostgreSQL URLs for asyncpg + Supabase Session/Transaction poolers."""
    cleaned = raw_url.strip()
    if "[your-password]" in cleaned.lower() or "[your-database-password]" in cleaned.lower():
        raise ValueError("DATABASE_URL still contains the Supabase password placeholder brackets.")
    url = make_url(cleaned)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+asyncpg")

    query = dict(url.query)
    connect_args: dict[str, Any] = {}

    raw_sslmode = str(query.pop("sslmode", "")).strip().lower()
    raw_pgbouncer = str(query.pop("pgbouncer", "")).strip().lower()

    host = (url.host or "").lower()
    is_supabase_pooler = host.endswith(".pooler.supabase.com")
    is_supabase_cloud = host.endswith(".supabase.co") or is_supabase_pooler

    if raw_sslmode in {"require", "verify-ca", "verify-full"} or (
        is_supabase_cloud and raw_sslmode != "disable"
    ):
        connect_args["ssl"] = "require"

    # Disable asyncpg prepared statement cache on Supavisor / PgBouncer poolers
    if url.port == 6543 or raw_pgbouncer == "true" or is_supabase_pooler:
        connect_args["statement_cache_size"] = 0

    normalized_url = url.set(query=query).render_as_string(hide_password=False)
    return normalized_url, connect_args


class DatabaseManager:
    """Manages the async SQLAlchemy engine and session factory."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        normalized_url, connect_args = normalize_database_url_and_connect_args(
            settings.database_url
        )
        connect_args.setdefault("timeout", max(settings.db_health_timeout_seconds, 5.0))
        self._engine: AsyncEngine = create_async_engine(
            normalized_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args=connect_args,
        )
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            yield session

    async def check_health(self) -> bool:
        """Run a bounded SELECT 1 probe against PostgreSQL."""
        try:
            async with asyncio.timeout(self._settings.db_health_timeout_seconds):
                async with self._engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.warning("database_health_check_failed", **_extract_safe_db_error_context(exc))
            return False

    async def dispose(self) -> None:
        await self._engine.dispose()


_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(get_settings())
    return _db_manager


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an async database session."""
    async for session in get_db_manager().session():
        yield session
