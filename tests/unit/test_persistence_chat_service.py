"""Unit tests for ChatService with persisted conversation history."""

import pytest

from app.core.exceptions import ValidationError
from app.db.exceptions import ConversationNotFoundError
from app.db.repositories.conversation import SQLAlchemyConversationRepository
from app.domain.messages import MessageRole
from app.llm.mock import MockLLMService
from app.services.chat import ChatService


@pytest.mark.asyncio
async def test_chat_service_creates_new_conversation(
    test_repository: SQLAlchemyConversationRepository,
) -> None:
    """Verify ChatService generates and persists a new conversation ID when none provided."""
    mock_llm = MockLLMService(default_response="Assistant reply 1")
    service = ChatService(llm_service=mock_llm, conversation_repository=test_repository)

    response, conv_id = await service.process_message("Hello there")

    assert conv_id is not None
    assert response.text == "Assistant reply 1"

    # Verify messages are persisted in repository
    history = await test_repository.get_history(conv_id)
    assert len(history) == 2
    assert history[0].role == MessageRole.USER
    assert history[0].text == "Hello there"
    assert history[1].role == MessageRole.ASSISTANT
    assert history[1].text == "Assistant reply 1"


@pytest.mark.asyncio
async def test_chat_service_continues_existing_conversation(
    test_repository: SQLAlchemyConversationRepository,
) -> None:
    """Verify ChatService loads historical turns and passes full context to LangGraph."""
    mock_llm = MockLLMService(default_response="Turn 1 reply")
    service = ChatService(llm_service=mock_llm, conversation_repository=test_repository)

    # Turn 1
    _, conv_id = await service.process_message("My favorite framework is FastAPI")

    # Turn 2 using returned conversation ID
    mock_llm.default_response = "Turn 2 reply"
    _, continued_conv_id = await service.process_message(
        message="What is my favorite framework?",
        conversation_id=conv_id,
    )

    assert continued_conv_id == conv_id

    # Verify MockLLM received the complete 3-message sequence for Turn 2 (Turn 1 User + Turn 1 Asst + Turn 2 User)
    last_call_messages = mock_llm.recorded_calls[-1]
    assert len(last_call_messages) == 3
    assert last_call_messages[0].text == "My favorite framework is FastAPI"
    assert last_call_messages[1].text == "Turn 1 reply"
    assert last_call_messages[2].text == "What is my favorite framework?"

    # Verify repository now contains 4 total messages
    history = await test_repository.get_history(conv_id)
    assert len(history) == 4


@pytest.mark.asyncio
async def test_chat_service_nonexistent_conversation_raises_not_found(
    test_repository: SQLAlchemyConversationRepository,
) -> None:
    """Verify ChatService raises ConversationNotFoundError for unknown conversation ID."""
    mock_llm = MockLLMService()
    service = ChatService(llm_service=mock_llm, conversation_repository=test_repository)

    with pytest.raises(ConversationNotFoundError) as exc_info:
        await service.process_message(
            message="Hello",
            conversation_id="nonexistent-uuid-12345",
        )

    assert exc_info.value.status_code == 404
    assert "nonexistent-uuid-12345" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_chat_service_empty_input_validation(
    test_repository: SQLAlchemyConversationRepository,
) -> None:
    """Verify ChatService validates non-empty message input."""
    mock_llm = MockLLMService()
    service = ChatService(llm_service=mock_llm, conversation_repository=test_repository)

    with pytest.raises(ValidationError):
        await service.process_message(message="   ")
