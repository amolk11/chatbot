"""Unit tests for global FastAPI exception handlers and error contracts."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.core.exceptions import (
    ChatbotError,
    ConfigurationError,
    ResourceNotFoundError,
    ValidationError,
)
from app.main import create_app


class DummyRequest(BaseModel):
    """Payload model for validation testing."""

    query: str
    limit: int


@pytest.fixture
def error_test_app() -> FastAPI:
    """FastAPI test app with dedicated error-triggering endpoints."""
    app = create_app()

    @app.get("/test/chatbot-error")
    async def trigger_chatbot_error() -> None:
        raise ChatbotError("Custom application error", code="CUSTOM_APP_ERROR", status_code=400)

    @app.get("/test/validation-error")
    async def trigger_domain_validation_error() -> None:
        raise ValidationError(
            "Invalid input parameter", details={"field": "query", "reason": "empty"}
        )

    @app.get("/test/resource-not-found")
    async def trigger_not_found_error() -> None:
        raise ResourceNotFoundError("Conversation session was not found", details={"id": "123"})

    @app.get("/test/configuration-error")
    async def trigger_config_error() -> None:
        raise ConfigurationError("Database credentials missing")

    @app.get("/test/unhandled-exception")
    async def trigger_unhandled_error() -> None:
        raise RuntimeError("Unexpected zero-division or crash")

    @app.post("/test/pydantic-validation")
    async def trigger_pydantic_validation(body: DummyRequest) -> dict[str, str]:
        return {"query": body.query}

    return app


@pytest.fixture
async def error_client(error_test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client targeting the error test application."""
    transport = ASGITransport(app=error_test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_chatbot_error_response_format(error_client: AsyncClient) -> None:
    """Verify ChatbotError returns structured ErrorResponse with status and code."""
    response = await error_client.get("/test/chatbot-error")

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "CUSTOM_APP_ERROR"
    assert data["error"]["message"] == "Custom application error"
    assert "correlation_id" in data["error"]
    assert response.headers["X-Correlation-ID"] == data["error"]["correlation_id"]


@pytest.mark.asyncio
async def test_validation_error_response_format(error_client: AsyncClient) -> None:
    """Verify domain ValidationError returns 422 with details dict."""
    response = await error_client.get("/test/validation-error")

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["details"] == {"field": "query", "reason": "empty"}


@pytest.mark.asyncio
async def test_resource_not_found_response_format(error_client: AsyncClient) -> None:
    """Verify ResourceNotFoundError returns 404 with details."""
    response = await error_client.get("/test/resource-not-found")

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_configuration_error_response_format(error_client: AsyncClient) -> None:
    """Verify ConfigurationError returns 500 status."""
    response = await error_client.get("/test/configuration-error")

    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "CONFIGURATION_ERROR"


@pytest.mark.asyncio
async def test_pydantic_request_validation_error(error_client: AsyncClient) -> None:
    """Verify FastAPI/Pydantic request payload validation returns 422 with sanitized field details."""
    response = await error_client.post("/test/pydantic-validation", json={"limit": "not-an-int"})

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(data["error"]["details"], list)
    assert len(data["error"]["details"]) > 0


@pytest.mark.asyncio
async def test_http_404_not_found(error_client: AsyncClient) -> None:
    """Verify accessing an unknown endpoint returns structured HTTP_404 ErrorResponse."""
    response = await error_client.get("/nonexistent-endpoint")

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "HTTP_404"
    assert "Not Found" in data["error"]["message"]


@pytest.mark.asyncio
async def test_unhandled_exception_returns_safe_500(error_client: AsyncClient) -> None:
    """Verify unhandled exceptions return safe 500 error without exposing stack traces."""
    response = await error_client.get("/test/unhandled-exception")

    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    # Ensure internal exception string is not leaked to client
    assert "RuntimeError" not in data["error"]["message"]
    assert "Unexpected zero-division" not in data["error"]["message"]
    assert data["error"]["correlation_id"] is not None
