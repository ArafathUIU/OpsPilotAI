"""Liveness and readiness health endpoints."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.core.config import get_settings
from src.persistence.session import check_db_health, check_redis_health

router = APIRouter(tags=["Health & Status"])
settings = get_settings()


class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str


class ReadinessResponse(BaseModel):
    status: str
    database: bool
    redis: bool
    details: dict[str, str]


@router.get("/health", response_model=HealthResponse, summary="Liveness Probe")
async def health_check() -> HealthResponse:
    """Returns basic liveness status to orchestrators and load balancers."""
    return HealthResponse(
        status="ok",
        environment=settings.ENVIRONMENT,
        version="0.1.0",
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness Probe",
    responses={
        status.HTTP_200_OK: {"description": "All required subsystems ready"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Subsystem unavailable"},
    },
)
async def readiness_check() -> JSONResponse:
    """Verifies that all external dependencies (PostgreSQL, Redis) are healthy."""
    db_ok = await check_db_health()
    redis_ok = await check_redis_health()

    is_ready = db_ok  # Database is mandatory; redis can be soft in test/dev
    http_status = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    payload = ReadinessResponse(
        status="ready" if is_ready else "unready",
        database=db_ok,
        redis=redis_ok,
        details={
            "database": "connected" if db_ok else "unreachable",
            "redis": "connected" if redis_ok else "unreachable",
        },
    )
    return JSONResponse(status_code=http_status, content=payload.model_dump())
