"""Unit tests for cache adapters and serialization."""

from unittest.mock import AsyncMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.cache.exceptions import CacheConnectionError, CacheSerializationError
from app.cache.memory import InMemoryCache
from app.cache.redis import RedisCacheAdapter
from app.cache.serialization import deserialize_cached_response, serialize_cached_response
from app.domain.messages import CanonicalMessage, MessageRole


@pytest.mark.asyncio
async def test_in_memory_cache_crud_and_ttl() -> None:
    """Verify basic CRUD and TTL expiration in InMemoryCache."""
    cache = InMemoryCache()

    # Get non-existent
    assert await cache.get("key1") is None

    # Set and Get
    await cache.set("key1", "val1", ttl=3600)
    assert await cache.get("key1") == "val1"

    # Delete
    await cache.delete("key1")
    assert await cache.get("key1") is None

    # Expiration simulation
    await cache.set("key_exp", "val_exp", ttl=1)
    with patch("time.monotonic", return_value=1000000.0):
        assert await cache.get("key_exp") is None

    # Close
    await cache.set("key2", "val2")
    await cache.close()
    assert await cache.get("key2") is None


@pytest.mark.asyncio
async def test_redis_adapter_operations_and_error_handling() -> None:
    """Verify RedisCacheAdapter delegation and error wrapping."""
    adapter = RedisCacheAdapter("redis://localhost:6379/0")

    mock_client = AsyncMock()
    adapter._client = mock_client

    # GET
    mock_client.get.return_value = "cached_val"
    val = await adapter.get("test_key")
    assert val == "cached_val"
    mock_client.get.assert_awaited_once_with("test_key")

    # SET with TTL
    await adapter.set("test_key", "new_val", ttl=60)
    mock_client.set.assert_awaited_once_with(name="test_key", value="new_val", ex=60)

    # DELETE
    await adapter.delete("test_key")
    mock_client.delete.assert_awaited_once_with("test_key")

    # Error isolation
    mock_client.get.side_effect = RedisConnectionError("Connection refused")
    with pytest.raises(CacheConnectionError):
        await adapter.get("broken_key")

    # Close
    await adapter.close()
    mock_client.aclose.assert_awaited_once()


def test_serialization_and_deserialization_roundtrip() -> None:
    """Verify serializing and deserializing a CanonicalMessage assistant reply."""
    original_msg = CanonicalMessage.from_text(
        text="Hello, I am your assistant!",
        role=MessageRole.ASSISTANT,
    )

    serialized = serialize_cached_response(original_msg)
    assert isinstance(serialized, str)
    assert "Hello, I am your assistant!" in serialized

    restored = deserialize_cached_response(serialized)
    assert restored.role == MessageRole.ASSISTANT
    assert restored.text == "Hello, I am your assistant!"
    # Ensure fresh message ID is generated
    assert restored.id is not None
    assert len(restored.id) > 0


def test_deserialization_malformed_json_raises_cache_serialization_error() -> None:
    """Verify malformed JSON raises CacheSerializationError."""
    with pytest.raises(CacheSerializationError):
        deserialize_cached_response("not valid json")

    with pytest.raises(CacheSerializationError):
        deserialize_cached_response('{"invalid_schema": 123}')
