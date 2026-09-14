"""Unit tests for the ChatService application orchestration layer."""

import pytest

from app.core.exceptions import ValidationError
from app.domain.messages import MessageRole
from app.llm.exceptions import LLMTimeoutError
from app.llm.mock import MockLLMService
from app.services.chat import ChatService


@pytest.mark.asyncio
async def test_chat_service_process_message_success() -> None:
    """Verify ChatService orchestrates workflow and produces canonical assistant reply."""
    mock_llm = MockLLMService(default_response="Service test response")
    service = ChatService(llm_service=mock_llm)

    response = await service.process_message(
        message="What is the speed of light?",
        conversation_id="conv-123",
    )

    assert response.role == MessageRole.ASSISTANT
    assert response.text == "Service test response"
    assert len(mock_llm.recorded_calls) == 1
    assert mock_llm.recorded_calls[0][0].text == "What is the speed of light?"


@pytest.mark.asyncio
async def test_chat_service_empty_input_validation() -> None:
    """Verify ChatService rejects empty or whitespace-only messages."""
    mock_llm = MockLLMService()
    service = ChatService(llm_service=mock_llm)

    with pytest.raises(ValidationError) as exc_info:
        await service.process_message(message="   ")

    assert "cannot be empty" in str(exc_info.value.message)
    assert len(mock_llm.recorded_calls) == 0


@pytest.mark.asyncio
async def test_chat_service_propagates_llm_exceptions() -> None:
    """Verify ChatService properly bubbles up downstream LLM errors."""
    mock_llm = MockLLMService(
        should_fail=True,
        failure_exception=LLMTimeoutError("LLM timed out"),
    )
    service = ChatService(llm_service=mock_llm)

    with pytest.raises(LLMTimeoutError) as exc_info:
        await service.process_message(message="Hello")

    assert exc_info.value.code == "LLM_TIMEOUT_ERROR"
    assert exc_info.value.status_code == 504
