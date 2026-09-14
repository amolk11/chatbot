"""Unit tests for ChatService integration with caching layer."""

from unittest.mock import AsyncMock

import pytest

from app.cache.exceptions import CacheConnectionError
from app.cache.memory import InMemoryCache
from app.db.repositories.conversation import SQLAlchemyConversationRepository
from app.domain.messages import CanonicalMessage, MessageRole
from app.llm.mock import MockLLMService
from app.services.chat import ChatService


@pytest.mark.asyncio
async def test_chat_service_cache_hit_avoids_duplicate_llm_calls(
    test_repository: SQLAlchemyConversationRepository,
) -> None:
    """Verify that an identical second request hits cache, avoiding LLM call while persisting turn."""
    mock_llm = MockLLMService()
    cache = InMemoryCache()
    service = ChatService(
        llm_service=mock_llm,
        conversation_repository=test_repository,
        cache=cache,
        cache_enabled=True,
        cache_ttl_seconds=3600,
    )

    conv_id = await test_repository.create_conversation()

    # Request 1 (Cache MISS -> LLM called)
    resp_1, c_id_1 = await service.process_message(
        message="What is the speed of light?",
        conversation_id=conv_id,
    )
    assert resp_1 is not None
    assert c_id_1 == conv_id

    # Verify 2 messages persisted in DB (User + Assistant)
    history_1 = await test_repository.get_history(conv_id)
    assert len(history_1) == 2
    assert history_1[0].text == "What is the speed of light?"
    assert history_1[1].text == "This is a deterministic mock assistant response."

    # Manually reset conversation to repeat identical turn context for test
    # (Or test with a fresh conversation session with same history)
    # Let's verify repeat turn in a new conversation with same context
    conv_id_2 = await test_repository.create_conversation()
    # If we issue the exact same prompt in a new conversation without prior history, the context is identical
    # Note: cache key includes conversation_id, so cache hit occurs for same conversation_id and context
    # If we simulate a cache hit by placing the response in cache for conv_id_2:
    from app.cache.keys import build_chat_cache_key
    from app.cache.serialization import serialize_cached_response

    user_msg_2 = CanonicalMessage.from_text("What is the speed of light?", role=MessageRole.USER)
    key_conv_2 = build_chat_cache_key(
        conversation_id=conv_id_2,
        history=[],
        current_user_message=user_msg_2,
        provider=mock_llm.provider_name,
        model=mock_llm.model_name,
    )
    await cache.set(key_conv_2, serialize_cached_response(resp_1), ttl=3600)

    # Now execute turn on conv_id_2 with MockLLM set to fail if invoked
    failing_llm = MockLLMService(should_fail=True)
    service_hit = ChatService(
        llm_service=failing_llm,
        conversation_repository=test_repository,
        cache=cache,
        cache_enabled=True,
        cache_ttl_seconds=3600,
    )

    resp_2, c_id_2 = await service_hit.process_message(
        message="What is the speed of light?",
        conversation_id=conv_id_2,
    )

    # Response returned successfully from cache without invoking failing LLM
    assert resp_2.text == resp_1.text
    assert c_id_2 == conv_id_2

    # Verify the turn was still durably persisted to the database
    history_2 = await test_repository.get_history(conv_id_2)
    assert len(history_2) == 2
    assert history_2[0].text == "What is the speed of light?"
    assert history_2[1].text == resp_1.text


@pytest.mark.asyncio
async def test_chat_service_cache_miss_populates_cache(
    test_repository: SQLAlchemyConversationRepository,
) -> None:
    """Verify that a cache miss calls LLM, persists turn, and writes to cache."""
    mock_llm = MockLLMService()
    cache = InMemoryCache()
    service = ChatService(
        llm_service=mock_llm,
        conversation_repository=test_repository,
        cache=cache,
        cache_enabled=True,
    )

    conv_id = await test_repository.create_conversation()
    resp, _ = await service.process_message("Hello from test", conversation_id=conv_id)

    assert resp is not None
    # Verify cache is populated (keys in cache store)
    assert len(cache._store) == 1


@pytest.mark.asyncio
async def test_chat_service_cache_get_failure_falls_back_to_llm(
    test_repository: SQLAlchemyConversationRepository,
) -> None:
    """Verify that if cache.get fails, ChatService smoothly falls back to normal LLM generation."""
    mock_llm = MockLLMService()
    faulty_cache = AsyncMock()
    faulty_cache.get.side_effect = CacheConnectionError("Redis connection timed out")

    service = ChatService(
        llm_service=mock_llm,
        conversation_repository=test_repository,
        cache=faulty_cache,
        cache_enabled=True,
    )

    conv_id = await test_repository.create_conversation()
    resp, _ = await service.process_message("Hello despite cache failure", conversation_id=conv_id)

    assert resp is not None
    assert resp.text == "This is a deterministic mock assistant response."

    # Verify turn is persisted in database
    history = await test_repository.get_history(conv_id)
    assert len(history) == 2


@pytest.mark.asyncio
async def test_chat_service_cache_set_failure_does_not_break_request(
    test_repository: SQLAlchemyConversationRepository,
) -> None:
    """Verify that if cache.set fails, the request still succeeds and database is updated."""
    mock_llm = MockLLMService()
    faulty_cache = AsyncMock()
    faulty_cache.get.return_value = None
    faulty_cache.set.side_effect = CacheConnectionError("Redis write failed")

    service = ChatService(
        llm_service=mock_llm,
        conversation_repository=test_repository,
        cache=faulty_cache,
        cache_enabled=True,
    )

    conv_id = await test_repository.create_conversation()
    resp, _ = await service.process_message("Hello with write failure", conversation_id=conv_id)

    assert resp is not None
    history = await test_repository.get_history(conv_id)
    assert len(history) == 2


@pytest.mark.asyncio
async def test_chat_service_malformed_cache_entry_treated_as_miss(
    test_repository: SQLAlchemyConversationRepository,
) -> None:
    """Verify that malformed cache payload is safely handled as a cache miss."""
    mock_llm = MockLLMService()
    cache = InMemoryCache()
    await cache.set("corrupted_key", "invalid json data {{{")

    service = ChatService(
        llm_service=mock_llm,
        conversation_repository=test_repository,
        cache=cache,
        cache_enabled=True,
    )

    # Mock build_chat_cache_key to point to corrupted_key
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.services.chat.build_chat_cache_key", lambda **_: "corrupted_key")
        conv_id = await test_repository.create_conversation()
        resp, _ = await service.process_message("Testing corrupt payload", conversation_id=conv_id)

    assert resp is not None
    assert resp.text == "This is a deterministic mock assistant response."


@pytest.mark.asyncio
async def test_chat_service_caching_disabled(
    test_repository: SQLAlchemyConversationRepository,
) -> None:
    """Verify that when cache_enabled=False, cache operations are bypassed."""
    mock_llm = MockLLMService()
    cache_spy = AsyncMock()

    service = ChatService(
        llm_service=mock_llm,
        conversation_repository=test_repository,
        cache=cache_spy,
        cache_enabled=False,
    )

    conv_id = await test_repository.create_conversation()
    resp, _ = await service.process_message("Cache disabled message", conversation_id=conv_id)

    assert resp is not None
    cache_spy.get.assert_not_called()
    cache_spy.set.assert_not_called()
