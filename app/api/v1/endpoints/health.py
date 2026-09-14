"""Health and readiness probe endpoint definitions."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_app_settings
from app.core.config import Settings
from app.core.exceptions import ExternalServiceError
from app.db.session import check_database_connection, get_session_factory
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
    description="Determines whether the application and its critical persistence dependencies are ready to accept traffic.",
)
async def readiness_check(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ReadinessResponse:
    """Readiness probe verifying API state and database connectivity."""
    session_factory = get_session_factory(settings)
    is_db_ready = await check_database_connection(session_factory)

    checks = {
        "api": "ready",
        "database": "ready" if is_db_ready else "unavailable",
    }

    if not is_db_ready:
        raise ExternalServiceError(
            message="Database connectivity check failed during readiness probe.",
            code="DATABASE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=checks,
        )

    return ReadinessResponse(
        status="ready",
        version=settings.app_version,
        environment=settings.app_env.value,
        checks=checks,
    )
