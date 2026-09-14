"""API tests for the POST /api/v1/chat endpoint with persistent conversations."""

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, get_llm_service
from app.llm.exceptions import LLMProviderError, LLMTimeoutError
from app.llm.mock import MockLLMService
from app.main import create_app

if TYPE_CHECKING:
    from fastapi import FastAPI


@pytest.mark.asyncio
async def test_chat_api_first_turn_generates_conversation_id(async_client: AsyncClient) -> None:
    """Verify POST /api/v1/chat without conversation_id generates a new conversation ID and returns 200."""
    payload = {
        "message": "echo: Hello from FastAPI Chat!",
    }
    response = await async_client.post("/api/v1/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"]["role"] == "assistant"
    assert data["message"]["text"] == "Echo: Hello from FastAPI Chat!"
    assert data["conversation_id"] is not None
    assert len(data["conversation_id"]) > 0
    assert "X-Correlation-ID" in response.headers


@pytest.mark.asyncio
async def test_chat_api_continuation_with_existing_conversation_id(
    async_client: AsyncClient,
) -> None:
    """Verify continuing an existing conversation by passing the returned conversation_id."""
    # Turn 1
    resp_turn_1 = await async_client.post("/api/v1/chat", json={"message": "echo: First message"})
    assert resp_turn_1.status_code == 200
    conv_id = resp_turn_1.json()["conversation_id"]

    # Turn 2
    resp_turn_2 = await async_client.post(
        "/api/v1/chat",
        json={"message": "echo: Second message", "conversation_id": conv_id},
    )
    assert resp_turn_2.status_code == 200
    assert resp_turn_2.json()["conversation_id"] == conv_id
    assert resp_turn_2.json()["message"]["text"] == "Echo: Second message"


@pytest.mark.asyncio
async def test_chat_api_unknown_conversation_id_returns_404(async_client: AsyncClient) -> None:
    """Verify providing an unknown conversation ID returns HTTP 404 with structured error."""
    payload = {
        "message": "Hello",
        "conversation_id": "nonexistent-conversation-uuid-9999",
    }
    response = await async_client.post("/api/v1/chat", json=payload)

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "CONVERSATION_NOT_FOUND"
    assert "nonexistent-conversation-uuid-9999" in data["error"]["message"]
    assert "correlation_id" in data["error"]


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
async def test_chat_api_llm_provider_error_handling(test_db_session: AsyncSession) -> None:
    """Verify downstream LLM provider failure is mapped to 502 with structured error response."""
    test_app: FastAPI = create_app()

    failing_llm = MockLLMService(
        should_fail=True,
        failure_exception=LLMProviderError("Provider unavailable", details={"provider": "mock"}),
    )
    test_app.dependency_overrides[get_llm_service] = lambda: failing_llm

    async def override_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    test_app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/chat", json={"message": "Hello"})

    assert response.status_code == 502
    data = response.json()
    assert data["error"]["code"] == "LLM_PROVIDER_ERROR"
    assert "Provider unavailable" in data["error"]["message"]
    assert "correlation_id" in data["error"]


@pytest.mark.asyncio
async def test_chat_api_llm_timeout_error_handling(test_db_session: AsyncSession) -> None:
    """Verify downstream LLM timeout failure is mapped to 504 Gateway Timeout."""
    test_app: FastAPI = create_app()

    timing_out_llm = MockLLMService(
        should_fail=True,
        failure_exception=LLMTimeoutError("Provider request exceeded 30s timeout."),
    )
    test_app.dependency_overrides[get_llm_service] = lambda: timing_out_llm

    async def override_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db_session

    test_app.dependency_overrides[get_db_session] = override_db

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
