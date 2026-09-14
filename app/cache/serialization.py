"""Serialization and deserialization helpers for cached chat messages."""

import json
import logging
from typing import Any

from app.cache.exceptions import CacheSerializationError
from app.domain.messages import CanonicalMessage, MessageRole, TextContentBlock

logger = logging.getLogger("app.cache.serialization")


def serialize_cached_response(message: CanonicalMessage) -> str:
    """Serialize a CanonicalMessage assistant response into a compact JSON string.

    Args:
        message: CanonicalMessage instance.

    Returns:
        JSON string representation.

    Raises:
        CacheSerializationError: If serialization fails.
    """
    try:
        payload = {
            "version": 1,
            "role": message.role.value,
            "content": [block.model_dump() for block in message.content],
        }
        return json.dumps(payload, separators=(",", ":"))
    except Exception as exc:
        logger.error("Failed to serialize CanonicalMessage to cache payload: %s", exc)
        raise CacheSerializationError(f"Could not serialize cache payload: {exc}") from exc


def deserialize_cached_response(raw_data: str) -> CanonicalMessage:
    """Deserialize a cached JSON payload into a CanonicalMessage assistant response.

    Assigns a fresh message UUID and UTC timestamp for the current turn.

    Args:
        raw_data: JSON string payload from cache.

    Returns:
        CanonicalMessage instance.

    Raises:
        CacheSerializationError: If payload is malformed or schema validation fails.
    """
    try:
        data: dict[str, Any] = json.loads(raw_data)
        role = MessageRole(data["role"])
        raw_content = data["content"]
        content_blocks = [TextContentBlock.model_validate(block) for block in raw_content]

        return CanonicalMessage(
            role=role,
            content=content_blocks,
        )
    except Exception as exc:
        logger.warning("Failed to deserialize cached response payload: %s", exc)
        raise CacheSerializationError(f"Malformed or incompatible cached data: {exc}") from exc
