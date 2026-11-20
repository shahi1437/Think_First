import re
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.deps import get_ml_classifier_service
from app.api.v1.health import health_router
from app.api.v1.router import api_v1_router
from app.core.config import Settings, get_settings
from app.core.database import get_db_manager
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
logger = get_logger(__name__)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.app_env != "test":
        get_ml_classifier_service(settings).warmup()
    logger.info(
        "application_startup",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )
    yield
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

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

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_v1_router)

    return app


app = create_app()
