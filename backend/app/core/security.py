import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
import jwt
from fastapi import status
from jwt import InvalidTokenError, PyJWK

from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

ALLOWED_ASYMMETRIC_ALGORITHMS = frozenset({"RS256", "ES256", "EdDSA"})


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    """Verified identity extracted from a Supabase JWT."""

    user_id: UUID
    email: str | None
    claims: dict[str, Any]


JWKSFetcher = Callable[[str], Awaitable[dict[str, Any]]]


async def _default_jwks_fetcher(jwks_url: str, timeout: float = 5.0) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("keys"), list):
            raise ValueError("Invalid JWKS payload structure")
        return payload


class SupabaseJWTVerifier:
    """Verifies Supabase asymmetric JWTs locally using cached JWKS public keys."""

    def __init__(
        self,
        settings: Settings,
        jwks_fetcher: JWKSFetcher | None = None,
    ) -> None:
        self._settings = settings
        self._jwks_fetcher = jwks_fetcher
        self._cached_keys: dict[str, dict[str, Any]] = {}
        self._cached_at: float = 0.0

    def _require_supabase_url(self) -> str:
        if not self._settings.supabase_url:
            raise AppError(
                code="AUTH_NOT_CONFIGURED",
                message="Authentication provider is not configured on the backend.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return self._settings.supabase_url.rstrip("/")

    async def _fetch_jwks(self, force_refresh: bool = False) -> dict[str, dict[str, Any]]:
        now = time.monotonic()
        if (
            not force_refresh
            and self._cached_keys
            and (now - self._cached_at) < self._settings.jwks_cache_ttl_seconds
        ):
            return self._cached_keys

        base_url = self._require_supabase_url()
        jwks_url = f"{base_url}/auth/v1/.well-known/jwks.json"
        try:
            if self._jwks_fetcher is not None:
                data = await self._jwks_fetcher(jwks_url)
            else:
                data = await _default_jwks_fetcher(
                    jwks_url, timeout=self._settings.jwks_fetch_timeout_seconds
                )
        except Exception as exc:
            logger.error("supabase_jwks_fetch_failed", error_type=type(exc).__name__)
            raise AppError(
                code="AUTH_PROVIDER_UNAVAILABLE",
                message="Unable to fetch authentication signing keys.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        keys_by_kid: dict[str, dict[str, Any]] = {}
        for item in data.get("keys", []):
            if isinstance(item, dict) and isinstance(item.get("kid"), str):
                keys_by_kid[item["kid"]] = item

        self._cached_keys = keys_by_kid
        self._cached_at = now
        return self._cached_keys

    async def verify_token(self, token: str) -> AuthenticatedPrincipal:
        """Cryptographically verify a Bearer JWT and extract the authenticated principal."""
        base_url = self._require_supabase_url()

        try:
            header = jwt.get_unverified_header(token)
        except InvalidTokenError as exc:
            raise AppError(
                code="UNAUTHORIZED",
                message="Invalid authentication token header.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ) from exc

        alg = header.get("alg")
        kid = header.get("kid")
        if not isinstance(alg, str) or alg not in ALLOWED_ASYMMETRIC_ALGORITHMS:
            raise AppError(
                code="UNAUTHORIZED",
                message="Unsupported token signing algorithm.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        if not isinstance(kid, str) or not kid:
            raise AppError(
                code="UNAUTHORIZED",
                message="Missing token signing key identifier.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        keys = await self._fetch_jwks(force_refresh=False)
        jwk_dict = keys.get(kid)
        if jwk_dict is None:
            keys = await self._fetch_jwks(force_refresh=True)
            jwk_dict = keys.get(kid)
        if jwk_dict is None:
            raise AppError(
                code="UNAUTHORIZED",
                message="Unknown token signing key identifier.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            signing_key = PyJWK.from_dict(jwk_dict).key
            claims = jwt.decode(
                token,
                key=signing_key,
                algorithms=[alg],
                audience=self._settings.supabase_jwt_audience,
                issuer=f"{base_url}/auth/v1",
                options={"require": ["sub", "exp", "aud", "iss"]},
            )
        except InvalidTokenError as exc:
            raise AppError(
                code="UNAUTHORIZED",
                message="Authentication token validation failed.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ) from exc

        sub = claims.get("sub")
        try:
            user_id = UUID(str(sub))
        except (ValueError, TypeError) as exc:
            raise AppError(
                code="UNAUTHORIZED",
                message="Invalid subject claim in authentication token.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            ) from exc

        email = claims.get("email")
        return AuthenticatedPrincipal(
            user_id=user_id,
            email=email.lower() if isinstance(email, str) else None,
            claims=dict(claims),
        )
