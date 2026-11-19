import asyncio
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manages the async SQLAlchemy engine and session factory."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine: AsyncEngine = create_async_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
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
            logger.warning("database_health_check_failed", error_type=type(exc).__name__)
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
