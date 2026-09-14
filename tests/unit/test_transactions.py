"""Unit tests verifying atomic turn persistence and failure rollback."""

import pytest

from app.db.exceptions import PersistenceError
from app.db.repositories.conversation import SQLAlchemyConversationRepository
from app.domain.messages import CanonicalMessage, MessageRole
from app.llm.exceptions import LLMTimeoutError
from app.llm.mock import MockLLMService
from app.services.chat import ChatService


@pytest.mark.asyncio
async def test_atomic_persistence_on_llm_failure(
    test_repository: SQLAlchemyConversationRepository,
) -> None:
    """Verify that if LLM fails during a turn, no partial messages or orphaned records are saved."""
    conv_id = await test_repository.create_conversation()

    # Initial successful turn
    user_msg_1 = CanonicalMessage.from_text("Turn 1 Question", role=MessageRole.USER)
    asst_msg_1 = CanonicalMessage.from_text("Turn 1 Answer", role=MessageRole.ASSISTANT)
    await test_repository.persist_turn(conv_id, user_msg_1, asst_msg_1)

    initial_history = await test_repository.get_history(conv_id)
    assert len(initial_history) == 2

    # Attempt Turn 2 with failing LLM
    failing_llm = MockLLMService(should_fail=True, failure_exception=LLMTimeoutError("LLM failed"))
    service = ChatService(llm_service=failing_llm, conversation_repository=test_repository)

    with pytest.raises(LLMTimeoutError):
        await service.process_message("Turn 2 Question", conversation_id=conv_id)

    # Verify history is unmodified and no partial user message was committed
    after_history = await test_repository.get_history(conv_id)
    assert len(after_history) == 2
    assert after_history[0].text == "Turn 1 Question"
    assert after_history[1].text == "Turn 1 Answer"


@pytest.mark.asyncio
async def test_failed_persist_turn_raises_persistence_error() -> None:
    """Verify repository wraps unexpected database exceptions in PersistenceError."""

    # Create repository with a closed or invalid session mock to simulate failure
    class FaultySession:
        async def get(self, *_args: object, **_kwargs: object) -> None:
            raise RuntimeError("Database disk full or connection dropped")

    faulty_repo = SQLAlchemyConversationRepository(session=FaultySession())  # type: ignore[arg-type]
    user_msg = CanonicalMessage.from_text("Hello", role=MessageRole.USER)
    asst_msg = CanonicalMessage.from_text("Hi", role=MessageRole.ASSISTANT)

    with pytest.raises(PersistenceError):
        await faulty_repo.persist_turn("conv-123", user_msg, asst_msg)
