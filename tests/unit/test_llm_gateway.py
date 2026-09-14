"""Unit tests for the LLM Gateway, Mock provider, and OpenAI adapter."""

from unittest.mock import AsyncMock, MagicMock

import openai
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.constants import AppEnvironment
from app.domain.messages import CanonicalMessage, MessageRole
from app.llm.exceptions import (
    LLMConfigurationError,
    LLMResponseParsingError,
    LLMTimeoutError,
)
from app.llm.factory import create_llm_service
from app.llm.mock import MockLLMService
from app.llm.providers.openai import OpenAILLMService


@pytest.mark.asyncio
async def test_mock_llm_deterministic_generation() -> None:
    """Verify MockLLMService returns default deterministic response."""
    mock_llm = MockLLMService(default_response="Mock answer")
    user_msg = CanonicalMessage.from_text("Hello there")

    response = await mock_llm.generate([user_msg])

    assert response.role == MessageRole.ASSISTANT
    assert response.text == "Mock answer"
    assert len(mock_llm.recorded_calls) == 1
    assert mock_llm.recorded_calls[0] == [user_msg]


@pytest.mark.asyncio
async def test_mock_llm_echo_mode() -> None:
    """Verify MockLLMService contextual echo trigger."""
    mock_llm = MockLLMService()
    user_msg = CanonicalMessage.from_text("echo: repeat after me")

    response = await mock_llm.generate([user_msg])

    assert response.role == MessageRole.ASSISTANT
    assert response.text == "Echo: repeat after me"


@pytest.mark.asyncio
async def test_mock_llm_simulated_failure() -> None:
    """Verify MockLLMService raises simulated exceptions when configured."""
    custom_error = LLMTimeoutError("Simulated timeout")
    mock_llm = MockLLMService(should_fail=True, failure_exception=custom_error)
    user_msg = CanonicalMessage.from_text("Hello")

    with pytest.raises(LLMTimeoutError) as exc_info:
        await mock_llm.generate([user_msg])

    assert exc_info.value.code == "LLM_TIMEOUT_ERROR"


@pytest.mark.asyncio
async def test_openai_adapter_successful_call() -> None:
    """Verify OpenAILLMService translates canonical messages to provider SDK and formats output."""
    adapter = OpenAILLMService(api_key="sk-mock-key-for-unit-testing", model="gpt-4o-mini")

    mock_chat_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "OpenAI generated answer"
    mock_chat_completion.id = "chatcmpl-test-123"
    mock_chat_completion.choices = [mock_choice]

    adapter._client.chat.completions.create = AsyncMock(return_value=mock_chat_completion)  # type: ignore[method-assign]

    user_msg = CanonicalMessage.from_text("What is Python?")
    response = await adapter.generate([user_msg])

    assert response.role == MessageRole.ASSISTANT
    assert response.text == "OpenAI generated answer"
    assert response.id == "chatcmpl-test-123"


@pytest.mark.asyncio
async def test_openai_adapter_timeout_error_mapping() -> None:
    """Verify openai.APITimeoutError translates to LLMTimeoutError."""
    adapter = OpenAILLMService(api_key="sk-mock-key", model="gpt-4o-mini")

    mock_request = MagicMock()
    adapter._client.chat.completions.create = AsyncMock(  # type: ignore[method-assign]
        side_effect=openai.APITimeoutError(request=mock_request)
    )

    user_msg = CanonicalMessage.from_text("Trigger timeout")

    with pytest.raises(LLMTimeoutError) as exc_info:
        await adapter.generate([user_msg])

    assert exc_info.value.code == "LLM_TIMEOUT_ERROR"
    assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_openai_adapter_empty_response_handling() -> None:
    """Verify empty choices list translates to LLMResponseParsingError."""
    adapter = OpenAILLMService(api_key="sk-mock-key", model="gpt-4o-mini")

    mock_empty_completion = MagicMock()
    mock_empty_completion.id = "chatcmpl-empty"
    mock_empty_completion.choices = []

    adapter._client.chat.completions.create = AsyncMock(return_value=mock_empty_completion)  # type: ignore[method-assign]

    user_msg = CanonicalMessage.from_text("Hello")

    with pytest.raises(LLMResponseParsingError):
        await adapter.generate([user_msg])


def test_create_llm_service_factory_mock() -> None:
    """Verify factory returns MockLLMService in testing mode or when provider is mock."""
    test_settings = Settings(app_env=AppEnvironment.TESTING, llm_provider="mock")
    service = create_llm_service(test_settings)
    assert isinstance(service, MockLLMService)


def test_create_llm_service_factory_openai() -> None:
    """Verify factory returns OpenAILLMService when configured for production."""
    prod_settings = Settings(
        app_env=AppEnvironment.PRODUCTION,
        llm_provider="openai",
        llm_api_key=SecretStr("sk-test-key-1234567890"),
        llm_model="gpt-4o-mini",
    )
    service = create_llm_service(prod_settings)
    assert isinstance(service, OpenAILLMService)


def test_create_llm_service_factory_missing_api_key() -> None:
    """Verify factory raises LLMConfigurationError if provider is openai but api key is missing."""
    invalid_settings = Settings(
        app_env=AppEnvironment.PRODUCTION,
        llm_provider="openai",
        llm_api_key=None,
    )
    with pytest.raises(LLMConfigurationError) as exc_info:
        create_llm_service(invalid_settings)

    assert "LLM_API_KEY must be configured" in str(exc_info.value.message)


def test_create_llm_service_factory_unsupported_provider() -> None:
    """Verify factory raises LLMConfigurationError for unknown providers."""
    bad_settings = Settings(
        app_env=AppEnvironment.PRODUCTION,
        llm_provider="unknown_ai_provider",
    )
    with pytest.raises(LLMConfigurationError):
        create_llm_service(bad_settings)
