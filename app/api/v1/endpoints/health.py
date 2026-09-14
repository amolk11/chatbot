"""Health and readiness probe endpoint definitions."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_app_settings
from app.core.config import Settings
from app.schemas.common import HealthResponse, ReadinessResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Confirms that the FastAPI application process is alive and responsive.",
)
async def health_check(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> HealthResponse:
    """Liveness probe returning application status, version, and environment."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.app_env.value,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Determines whether the application is fully initialized and ready to accept traffic.",
)
async def readiness_check(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ReadinessResponse:
    """Readiness probe extensible for future infrastructure dependency verification."""
    # Note: In Phase 2, there are no external dependencies (DB/Redis/LLM).
    # In future phases, readiness checks for database, cache, and LLM services will be registered here.
    checks = {
        "api": "ready",
    }
    return ReadinessResponse(
        status="ready",
        version=settings.app_version,
        environment=settings.app_env.value,
        checks=checks,
    )
