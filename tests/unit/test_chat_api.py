"""API tests for the POST /api/v1/chat endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_llm_service
from app.llm.exceptions import LLMProviderError, LLMTimeoutError
from app.llm.mock import MockLLMService
from app.main import create_app


@pytest.mark.asyncio
async def test_chat_api_endpoint_success(async_client: AsyncClient) -> None:
    """Verify POST /api/v1/chat returns 200 and standard ChatResponse schema."""
    payload = {
        "message": "echo: Hello from FastAPI Chat!",
        "conversation_id": "test-conv-001",
    }
    response = await async_client.post("/api/v1/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"]["role"] == "assistant"
    assert data["message"]["text"] == "Echo: Hello from FastAPI Chat!"
    assert data["conversation_id"] == "test-conv-001"
    assert "X-Correlation-ID" in response.headers


@pytest.mark.asyncio
async def test_chat_api_custom_correlation_id(async_client: AsyncClient) -> None:
    """Verify custom correlation ID is propagated in chat response headers."""
    custom_trace_id = "trace-client-chat-999"
    headers = {"X-Correlation-ID": custom_trace_id}
    payload = {"message": "Hello"}

    response = await async_client.post("/api/v1/chat", json=payload, headers=headers)

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == custom_trace_id


@pytest.mark.asyncio
async def test_chat_api_empty_message_validation(async_client: AsyncClient) -> None:
    """Verify sending an empty message returns 422 Unprocessable Entity."""
    response = await async_client.post("/api/v1/chat", json={"message": ""})

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "correlation_id" in data["error"]


@pytest.mark.asyncio
async def test_chat_api_missing_message_field(async_client: AsyncClient) -> None:
    """Verify missing required 'message' key returns 422 Unprocessable Entity."""
    response = await async_client.post("/api/v1/chat", json={"conversation_id": "conv-1"})

    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_chat_api_llm_provider_error_handling() -> None:
    """Verify downstream LLM provider failure is mapped to 502 with structured error response."""
    test_app = create_app()

    failing_llm = MockLLMService(
        should_fail=True,
        failure_exception=LLMProviderError("Provider unavailable", details={"provider": "mock"}),
    )
    test_app.dependency_overrides[get_llm_service] = lambda: failing_llm

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json={"message": "Hello"})

    assert response.status_code == 502
    data = response.json()
    assert data["error"]["code"] == "LLM_PROVIDER_ERROR"
    assert "Provider unavailable" in data["error"]["message"]
    assert "correlation_id" in data["error"]


@pytest.mark.asyncio
async def test_chat_api_llm_timeout_error_handling() -> None:
    """Verify downstream LLM timeout failure is mapped to 504 Gateway Timeout."""
    test_app = create_app()

    timing_out_llm = MockLLMService(
        should_fail=True,
        failure_exception=LLMTimeoutError("Provider request exceeded 30s timeout."),
    )
    test_app.dependency_overrides[get_llm_service] = lambda: timing_out_llm

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json={"message": "Hello"})

    assert response.status_code == 504
    data = response.json()
    assert data["error"]["code"] == "LLM_TIMEOUT_ERROR"
    assert "timeout" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_chat_api_openapi_registration(async_client: AsyncClient) -> None:
    """Verify POST /api/v1/chat is registered in OpenAPI schema."""
    response = await async_client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/chat" in schema["paths"]
    assert "post" in schema["paths"]["/api/v1/chat"]
    post_spec = schema["paths"]["/api/v1/chat"]["post"]
    assert "Execute Chat Turn" in post_spec["summary"]
