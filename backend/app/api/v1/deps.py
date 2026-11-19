from collections.abc import Callable, Coroutine
from functools import lru_cache
from typing import Any

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.errors import AppError
from app.core.security import AuthenticatedPrincipal, SupabaseJWTVerifier
from app.integrations.judge0.client import HttpJudge0Client, Judge0Client
from app.repositories.identity import IdentityRepository, SQLAlchemyIdentityRepository, UserRecord
from app.repositories.problems import ProblemRepository
from app.schemas.identity import RoleName
from app.services.execution.service import ExecutionService
from app.services.identity.service import IdentityService
from app.services.problems.service import ProblemService

_bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=8)
def _cached_verifier(
    supabase_url: str | None,
    supabase_jwt_audience: str,
    jwks_cache_ttl_seconds: int,
    jwks_fetch_timeout_seconds: float,
) -> SupabaseJWTVerifier:
    settings = Settings(
        supabase_url=supabase_url,
        supabase_jwt_audience=supabase_jwt_audience,
        jwks_cache_ttl_seconds=jwks_cache_ttl_seconds,
        jwks_fetch_timeout_seconds=jwks_fetch_timeout_seconds,
    )
    return SupabaseJWTVerifier(settings)


def get_jwt_verifier(
    settings: Settings = Depends(get_settings),
) -> SupabaseJWTVerifier:
    """Return cached Supabase asymmetric JWKS verifier for the active settings."""
    return _cached_verifier(
        settings.supabase_url,
        settings.supabase_jwt_audience,
        settings.jwks_cache_ttl_seconds,
        settings.jwks_fetch_timeout_seconds,
    )


def get_judge0_client(
    settings: Settings = Depends(get_settings),
) -> Judge0Client:
    """Return Judge0 CE HTTP execution client."""
    return HttpJudge0Client(settings)


def get_identity_repository(
    session: AsyncSession = Depends(get_db_session),
) -> IdentityRepository:
    return SQLAlchemyIdentityRepository(session)


def get_identity_service(
    repository: IdentityRepository = Depends(get_identity_repository),
) -> IdentityService:
    return IdentityService(repository)


def get_problem_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ProblemRepository:
    return ProblemRepository(session)


def get_problem_service(
    repository: ProblemRepository = Depends(get_problem_repository),
    judge0: Judge0Client = Depends(get_judge0_client),
) -> ProblemService:
    return ProblemService(repository=repository, judge0=judge0)


def get_execution_service(
    repository: ProblemRepository = Depends(get_problem_repository),
    judge0: Judge0Client = Depends(get_judge0_client),
    settings: Settings = Depends(get_settings),
) -> ExecutionService:
    return ExecutionService(repository=repository, judge0=judge0, settings=settings)


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    verifier: SupabaseJWTVerifier = Depends(get_jwt_verifier),
) -> AuthenticatedPrincipal:
    """Verify Bearer JWT on every protected route."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            code="UNAUTHORIZED",
            message="Missing or invalid Authorization header.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    return await verifier.verify_token(credentials.credentials)


async def get_current_user(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
    service: IdentityService = Depends(get_identity_service),
) -> UserRecord:
    """Resolve authenticated user along with authoritative DB-backed roles."""
    return await service.resolve_authenticated_user(principal)


def require_roles(
    *allowed_roles: RoleName,
) -> Callable[[UserRecord], Coroutine[Any, Any, UserRecord]]:
    """Dependency enforcing DB-backed role membership."""
    allowed_set = frozenset(allowed_roles)

    async def _role_guard(
        current_user: UserRecord = Depends(get_current_user),
    ) -> UserRecord:
        if not any(role in allowed_set for role in current_user.roles):
            raise AppError(
                code="FORBIDDEN",
                message="You do not have permission to perform this action.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return current_user

    return _role_guard
