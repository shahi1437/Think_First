from fastapi import APIRouter, Depends, Request, Response, status

from app.core.config import Settings, get_settings
from app.core.database import DatabaseManager, get_db_manager
from app.schemas.common import ApiMetaResponse, HealthLiveResponse, HealthReadyResponse

health_router = APIRouter(tags=["Health"])
meta_router = APIRouter(tags=["Meta"])


@health_router.get("/health/live", response_model=HealthLiveResponse)
async def health_live(
    settings: Settings = Depends(get_settings),
) -> HealthLiveResponse:
    """Process liveness endpoint."""
    return HealthLiveResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
    )


@health_router.get(
    "/health/ready",
    response_model=HealthReadyResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": HealthReadyResponse,
            "description": "One or more critical dependencies are unavailable.",
        }
    },
)
async def health_ready(
    response: Response,
    settings: Settings = Depends(get_settings),
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> HealthReadyResponse:
    """Readiness endpoint verifying real PostgreSQL connectivity."""
    db_ok = await db_manager.check_health()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthReadyResponse(
            status="degraded",
            service=settings.app_name,
            version=settings.app_version,
            database="unavailable",
        )
    return HealthReadyResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        database="ok",
    )


@meta_router.get("/meta", response_model=ApiMetaResponse)
async def api_meta(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ApiMetaResponse:
    """Versioned API metadata endpoint for client connectivity verification."""
    request_id = getattr(request.state, "request_id", "unknown")
    return ApiMetaResponse(
        service=settings.app_name,
        app_version=settings.app_version,
        environment=settings.app_env,
        request_id=request_id,
    )
