"""Global pytest fixtures and test configuration."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.constants import AppEnvironment, LogFormat, LogLevel
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Fixture providing isolated settings for testing."""
    return Settings(
        app_name="AI Chatbot Test",
        app_env=AppEnvironment.TESTING,
        log_level=LogLevel.DEBUG,
        log_format=LogFormat.CONSOLE,
        api_v1_prefix="/api/v1",
        rate_limit_per_minute=1000,
    )


@pytest.fixture
def test_app(test_settings: Settings) -> FastAPI:
    """Fixture providing a FastAPI test application instance."""
    return create_app(settings=test_settings)


@pytest.fixture
async def async_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Fixture providing an async HTTP test client."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
