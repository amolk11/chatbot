"""Deterministic conversation-aware cache key generator."""

import hashlib
import json
from collections.abc import Sequence

from app.domain.messages import CanonicalMessage, TextContentBlock

CACHE_VERSION_PREFIX = "chat:v1"


def build_chat_cache_key(
    conversation_id: str,
    history: Sequence[CanonicalMessage],
    current_user_message: CanonicalMessage,
    provider: str | None = None,
    model: str | None = None,
) -> str:
    """Generate a deterministic, context-sensitive SHA-256 cache key for a conversation turn.

    The cache key preimage incorporates:
    1. Chronological historical messages (role + content blocks)
    2. Current user message (role + content blocks)
    3. LLM provider and model identity

    Timestamps, message UUIDs, and transport metadata are explicitly excluded to
    ensure exact determinism across logically identical turns.

    Args:
        conversation_id: Unique conversation identifier.
        history: Preceding conversation history messages.
        current_user_message: Current user message turn.
        provider: Active LLM provider name (e.g. 'openai', 'mock').
        model: Active LLM model identifier (e.g. 'gpt-4o-mini').

    Returns:
        Formatted cache key string: `chat:v1:{conversation_id}:{sha256_hash}`
    """
    canonical_turns: list[dict[str, object]] = []

    # Sequence of all turns comprising the prompt context
    all_context_messages = [*history, current_user_message]

    for msg in all_context_messages:
        serialized_blocks: list[dict[str, str]] = []
        for block in msg.content:
            if isinstance(block, TextContentBlock):
                serialized_blocks.append({"type": block.type.value, "text": block.text})
            else:
                serialized_blocks.append(
                    {"type": str(block.type), "text": getattr(block, "text", "")}
                )

        canonical_turns.append(
            {
                "role": msg.role.value,
                "content": serialized_blocks,
            }
        )

    preimage_dict: dict[str, object] = {
        "provider": provider or "default",
        "model": model or "default",
        "messages": canonical_turns,
    }

    # Deterministic JSON serialization: sorted keys, compact separators
    preimage_bytes = json.dumps(preimage_dict, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    context_hash = hashlib.sha256(preimage_bytes).hexdigest()

    return f"{CACHE_VERSION_PREFIX}:{conversation_id}:{context_hash}"
