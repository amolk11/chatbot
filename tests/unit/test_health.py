"""Unit and API tests for health and readiness probes."""

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
async def test_readiness_check_endpoint(async_client: AsyncClient, test_settings: Settings) -> None:
    """Verify GET /health/ready returns 200 and component checks map."""
    response = await async_client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["version"] == test_settings.app_version
    assert data["environment"] == test_settings.app_env.value
    assert "checks" in data
    assert data["checks"]["api"] == "ready"
