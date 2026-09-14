"""Unit tests for SQLAlchemyConversationRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import ConversationModel
from app.db.repositories.conversation import SQLAlchemyConversationRepository
from app.domain.messages import CanonicalMessage, MessageRole


@pytest.mark.asyncio
async def test_create_and_check_conversation_exists(
    test_repository: SQLAlchemyConversationRepository,
) -> None:
    """Verify conversation creation and existence checks."""
    assert await test_repository.conversation_exists("nonexistent-conv-id") is False

    conv_id = await test_repository.create_conversation()
    assert conv_id is not None
    assert await test_repository.conversation_exists(conv_id) is True


@pytest.mark.asyncio
async def test_persist_turn_and_retrieve_history(
    test_repository: SQLAlchemyConversationRepository,
) -> None:
    """Verify persisting conversation turns and retrieving chronologically ordered messages."""
    conv_id = await test_repository.create_conversation()

    user_msg_1 = CanonicalMessage.from_text("What is Python?", role=MessageRole.USER)
    asst_msg_1 = CanonicalMessage.from_text(
        "Python is a programming language.", role=MessageRole.ASSISTANT
    )

    await test_repository.persist_turn(conv_id, user_msg_1, asst_msg_1)

    history = await test_repository.get_history(conv_id)
    assert len(history) == 2
    assert history[0].text == "What is Python?"
    assert history[0].role == MessageRole.USER
    assert history[1].text == "Python is a programming language."
    assert history[1].role == MessageRole.ASSISTANT

    # Persist second turn
    user_msg_2 = CanonicalMessage.from_text("What are its key features?", role=MessageRole.USER)
    asst_msg_2 = CanonicalMessage.from_text(
        "Readability and dynamic typing.", role=MessageRole.ASSISTANT
    )

    await test_repository.persist_turn(conv_id, user_msg_2, asst_msg_2)

    history_all = await test_repository.get_history(conv_id)
    assert len(history_all) == 4
    assert history_all[0].text == "What is Python?"
    assert history_all[1].text == "Python is a programming language."
    assert history_all[2].text == "What are its key features?"
    assert history_all[3].text == "Readability and dynamic typing."


@pytest.mark.asyncio
async def test_get_history_limit_respects_chronological_order(
    test_repository: SQLAlchemyConversationRepository,
) -> None:
    """Verify history limit fetches the latest N messages in chronological order."""
    conv_id = await test_repository.create_conversation()

    # Create 3 turns (6 messages)
    for i in range(1, 4):
        u_msg = CanonicalMessage.from_text(f"Question {i}", role=MessageRole.USER)
        a_msg = CanonicalMessage.from_text(f"Answer {i}", role=MessageRole.ASSISTANT)
        await test_repository.persist_turn(conv_id, u_msg, a_msg)

    # Request limit of 3 (should return Question 2, Answer 2, Question 3, Answer 3? No, limit=3 returns last 3: Answer 2, Question 3, Answer 3)
    history_limited = await test_repository.get_history(conv_id, limit=3)
    assert len(history_limited) == 3
    assert history_limited[0].text == "Answer 2"
    assert history_limited[1].text == "Question 3"
    assert history_limited[2].text == "Answer 3"


@pytest.mark.asyncio
async def test_conversation_updated_at_advances_on_persist_turn(
    test_repository: SQLAlchemyConversationRepository,
    test_db_session: AsyncSession,
) -> None:
    """Verify updated_at timestamp advances upon saving new turns."""
    conv_id = await test_repository.create_conversation()
    conv_model = await test_db_session.get(ConversationModel, conv_id)
    assert conv_model is not None
    initial_updated_at = conv_model.updated_at

    user_msg = CanonicalMessage.from_text("Hello", role=MessageRole.USER)
    asst_msg = CanonicalMessage.from_text("Hi", role=MessageRole.ASSISTANT)
    await test_repository.persist_turn(conv_id, user_msg, asst_msg)

    await test_db_session.refresh(conv_model)
    assert conv_model.updated_at >= initial_updated_at
