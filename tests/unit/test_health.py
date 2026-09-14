"""Unit and API tests for health and readiness probes."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.config import Settings


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: AsyncClient, test_settings: Settings) -> None:
    """Verify GET /health returns 200 and accurate system metadata."""
    response = await async_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == test_settings.app_version
    assert data["environment"] == test_settings.app_env.value
    assert "X-Correlation-ID" in response.headers


@pytest.mark.asyncio
async def test_health_check_v1_endpoint(async_client: AsyncClient, test_settings: Settings) -> None:
    """Verify GET /api/v1/health returns identical metadata when queried under version prefix."""
    response = await async_client.get(f"{test_settings.api_v1_prefix}/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == test_settings.app_version
    assert data["environment"] == test_settings.app_env.value


@pytest.mark.asyncio
async def test_readiness_check_endpoint_success(
    async_client: AsyncClient, test_settings: Settings
) -> None:
    """Verify GET /health/ready returns 200 and both API and Database ready status."""
    response = await async_client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["version"] == test_settings.app_version
    assert data["environment"] == test_settings.app_env.value
    assert "checks" in data
    assert data["checks"]["api"] == "ready"
    assert data["checks"]["database"] == "ready"


@pytest.mark.asyncio
async def test_readiness_check_endpoint_database_failure(async_client: AsyncClient) -> None:
    """Verify GET /health/ready returns 503 when database connectivity probe fails."""
    with patch(
        "app.api.v1.endpoints.health.check_database_connection",
        new=AsyncMock(return_value=False),
    ):
        response = await async_client.get("/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert "Database connectivity check failed" in data["error"]["message"]
    assert data["error"]["details"]["database"] == "unavailable"
