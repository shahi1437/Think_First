import ipaddress
import re
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.deps import get_ml_classifier_service
from app.api.v1.health import health_router
from app.api.v1.router import api_v1_router
from app.core.config import IPNetwork, Settings, get_settings
from app.core.database import get_db_manager
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import InMemorySlidingWindowRateLimiter
from app.schemas.common import ErrorResponse
from app.services.execution.embedded_worker import (
    EmbeddedExecutionWorker,
    start_embedded_worker_if_enabled,
    stop_embedded_worker,
)

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
logger = get_logger(__name__)


def _apply_security_headers(response: Response, *, path: str) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    )
    if path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")


def _parse_ip(raw: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    cleaned = raw.strip()
    if not cleaned:
        return None
    try:
        return ipaddress.ip_address(cleaned)
    except ValueError:
        return None


def _is_ip_in_networks(
    ip_addr: ipaddress.IPv4Address | ipaddress.IPv6Address,
    networks: Sequence[IPNetwork],
) -> bool:
    return any(ip_addr in network for network in networks)


def _extract_client_ip(
    request: Request,
    *,
    settings: Settings,
    trusted_networks: Sequence[IPNetwork],
) -> str:
    """Resolve client IP without trusting forwarding headers from untrusted peers.

    Forwarding headers are inspected ONLY when the direct TCP peer matches
    `TRUSTED_PROXY_CIDRS`. When trusted, an explicitly configured edge header
    (`TRUSTED_PROXY_CLIENT_IP_HEADER`) is checked first; otherwise `X-Forwarded-For`
    is walked right-to-left peeling at most `TRUSTED_PROXY_HOPS - 1` intermediate
    trusted proxy hops.
    """
    peer_host = (request.client.host or "").strip() if request.client else ""
    if not peer_host:
        return "unknown"

    peer_ip = _parse_ip(peer_host)
    if peer_ip is None or not trusted_networks or not _is_ip_in_networks(peer_ip, trusted_networks):
        return peer_host

    if settings.trusted_proxy_client_ip_header:
        edge_ip = _parse_ip(request.headers.get(settings.trusted_proxy_client_ip_header, ""))
        if edge_ip is not None:
            return str(edge_ip)

    forwarded = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded:
        hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
        max_intermediate_skips = max(settings.trusted_proxy_hops - 1, 0)
        skipped = 0
        for raw_hop in reversed(hops):
            parsed = _parse_ip(raw_hop)
            if parsed is None:
                return peer_host
            if skipped < max_intermediate_skips and _is_ip_in_networks(parsed, trusted_networks):
                skipped += 1
                continue
            return str(parsed)

    return str(peer_ip)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = getattr(app.state, "settings", None) or get_settings()
    embedded_worker: EmbeddedExecutionWorker | None = None
    if settings.app_env != "test":
        get_ml_classifier_service(settings).warmup()
        embedded_worker = start_embedded_worker_if_enabled(settings=settings)
    prod_issues = settings.validate_production_readiness()
    if prod_issues:
        logger.warning("production_config_warnings", warnings=prod_issues)
    logger.info(
        "application_startup",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        embedded_worker_active=embedded_worker is not None,
    )
    try:
        yield
    finally:
        if embedded_worker is not None:
            await stop_embedded_worker(embedded_worker)
        await get_db_manager().dispose()
        logger.info("application_shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct and configure the FastAPI application instance."""
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description="Modular monolith API for CodeMentor AI (Think_First).",
        lifespan=_lifespan,
        docs_url="/docs" if resolved_settings.app_env != "production" else None,
        redoc_url="/redoc" if resolved_settings.app_env != "production" else None,
    )
    app.state.settings = resolved_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    write_limiter = InMemorySlidingWindowRateLimiter(window_seconds=60.0)
    join_limiter = InMemorySlidingWindowRateLimiter(window_seconds=60.0)
    portal_verify_limiter = InMemorySlidingWindowRateLimiter(window_seconds=60.0)
    trusted_proxy_networks = resolved_settings.parsed_trusted_proxy_networks()

    @app.middleware("http")
    async def request_context_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming_id = request.headers.get("X-Request-ID", "").strip()
        request_id = incoming_id if _REQUEST_ID_PATTERN.match(incoming_id) else str(uuid.uuid4())
        request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        path = request.url.path
        content_length_raw = request.headers.get("Content-Length")
        if content_length_raw is not None:
            try:
                if int(content_length_raw) > resolved_settings.max_request_body_bytes:
                    payload = ErrorResponse(
                        code="PAYLOAD_TOO_LARGE",
                        message="Request body exceeds maximum allowed size.",
                        details={"max_bytes": resolved_settings.max_request_body_bytes},
                        request_id=request_id,
                    )
                    resp = JSONResponse(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        content=payload.model_dump(),
                    )
                    resp.headers["X-Request-ID"] = request_id
                    _apply_security_headers(resp, path=path)
                    return resp
            except ValueError:
                pass

        if (
            resolved_settings.rate_limit_enabled
            and request.method in _MUTATING_METHODS
            and path.startswith("/api/v1/")
        ):
            client_ip = _extract_client_ip(
                request,
                settings=resolved_settings,
                trusted_networks=trusted_proxy_networks,
            )
            if path.rstrip("/") == "/api/v1/student/classes/join":
                decision = join_limiter.check(
                    f"join:{client_ip}",
                    limit=resolved_settings.class_join_rate_limit_per_minute,
                )
            elif path.rstrip("/") == "/api/v1/users/me/verify-portal":
                decision = portal_verify_limiter.check(
                    f"portal_verify:{client_ip}",
                    limit=resolved_settings.portal_verify_rate_limit_per_minute,
                )
            else:
                decision = write_limiter.check(
                    f"write:{client_ip}",
                    limit=resolved_settings.api_write_rate_limit_per_minute,
                )
            if not decision.allowed:
                payload = ErrorResponse(
                    code="RATE_LIMITED",
                    message="Too many requests. Please slow down and try again shortly.",
                    details={"retry_after_seconds": decision.retry_after_seconds},
                    request_id=request_id,
                )
                resp = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content=payload.model_dump(),
                )
                resp.headers["Retry-After"] = str(decision.retry_after_seconds)
                resp.headers["X-Request-ID"] = request_id
                _apply_security_headers(resp, path=path)
                return resp

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        _apply_security_headers(response, path=path)
        logger.info(
            "http_request",
            method=request.method,
            path=path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        if duration_ms >= resolved_settings.slow_request_threshold_ms:
            logger.warning(
                "slow_http_request",
                method=request.method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        return response

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_v1_router)

    return app


app = create_app()
