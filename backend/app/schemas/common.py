from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Consistent structured API error response."""

    code: str = Field(..., examples=["VALIDATION_ERROR"])
    message: str = Field(..., examples=["Request validation failed."])
    details: dict[str, Any] | None = None
    request_id: str


class HealthLiveResponse(BaseModel):
    """Liveness check payload."""

    status: Literal["ok"] = "ok"
    service: str
    version: str


class HealthReadyResponse(BaseModel):
    """Readiness check payload reflecting real dependency probes."""

    status: Literal["ok", "degraded"]
    service: str
    version: str
    database: Literal["ok", "unavailable"]


class ApiMetaResponse(BaseModel):
    """API metadata response used for connectivity and contract verification."""

    service: str
    api_version: Literal["v1"] = "v1"
    app_version: str
    environment: str
    request_id: str


class PaginatedResponse[T](BaseModel):
    """Standard paginated collection envelope."""

    items: list[T]
    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)
