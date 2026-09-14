"""Unit tests for deterministic conversation cache key generation."""

from app.cache.keys import build_chat_cache_key
from app.domain.messages import CanonicalMessage, MessageRole


def test_cache_key_determinism() -> None:
    """Verify that identical conversation context produces the exact same cache key."""
    conv_id = "conv-deterministic-123"
    history = [
        CanonicalMessage.from_text("Hello", role=MessageRole.USER),
        CanonicalMessage.from_text("Hi there!", role=MessageRole.ASSISTANT),
    ]
    current_msg = CanonicalMessage.from_text("What is AI?", role=MessageRole.USER)

    key_1 = build_chat_cache_key(
        conversation_id=conv_id,
        history=history,
        current_user_message=current_msg,
        provider="mock",
        model="mock-model",
    )
    key_2 = build_chat_cache_key(
        conversation_id=conv_id,
        history=history,
        current_user_message=current_msg,
        provider="mock",
        model="mock-model",
    )

    assert key_1 == key_2
    assert key_1.startswith("chat:v1:conv-deterministic-123:")


def test_different_histories_produce_different_keys_critical() -> None:
    """Verify Section 23 requirement: different conversation histories must produce distinct cache keys."""
    # Conversation A: "My name is Amol."
    history_a = [
        CanonicalMessage.from_text("My name is Amol.", role=MessageRole.USER),
        CanonicalMessage.from_text("Nice to meet you, Amol!", role=MessageRole.ASSISTANT),
    ]
    # Conversation B: "My name is Rahul."
    history_b = [
        CanonicalMessage.from_text("My name is Rahul.", role=MessageRole.USER),
        CanonicalMessage.from_text("Nice to meet you, Rahul!", role=MessageRole.ASSISTANT),
    ]

    question = CanonicalMessage.from_text("What is my name?", role=MessageRole.USER)

    key_a = build_chat_cache_key(
        conversation_id="conv-common",
        history=history_a,
        current_user_message=question,
        provider="openai",
        model="gpt-4o-mini",
    )
    key_b = build_chat_cache_key(
        conversation_id="conv-common",
        history=history_b,
        current_user_message=question,
        provider="openai",
        model="gpt-4o-mini",
    )

    assert key_a != key_b


def test_evolving_conversation_history_changes_cache_key() -> None:
    """Verify Section 23 requirement: adding new messages to a conversation naturally invalidates old keys."""
    conv_id = "conv-evolving-99"
    q1 = CanonicalMessage.from_text("What is the capital of France?", role=MessageRole.USER)
    a1 = CanonicalMessage.from_text("Paris.", role=MessageRole.ASSISTANT)

    follow_up = CanonicalMessage.from_text("What is its population?", role=MessageRole.USER)

    # Key K1 with History H1 (empty)
    key_h1 = build_chat_cache_key(
        conversation_id=conv_id,
        history=[],
        current_user_message=follow_up,
    )

    # Key K2 with History H2 ([q1, a1])
    key_h2 = build_chat_cache_key(
        conversation_id=conv_id,
        history=[q1, a1],
        current_user_message=follow_up,
    )

    assert key_h1 != key_h2


def test_provider_and_model_differences_alter_cache_key() -> None:
    """Verify that differing LLM providers or models produce different cache keys."""
    conv_id = "conv-provider-check"
    msg = CanonicalMessage.from_text("Explain quantum computing", role=MessageRole.USER)

    key_openai = build_chat_cache_key(
        conversation_id=conv_id,
        history=[],
        current_user_message=msg,
        provider="openai",
        model="gpt-4o",
    )
    key_mock = build_chat_cache_key(
        conversation_id=conv_id,
        history=[],
        current_user_message=msg,
        provider="mock",
        model="mock-v1",
    )

    assert key_openai != key_mock


def test_message_ordering_alters_cache_key() -> None:
    """Verify that reversing history order produces a different cache key."""
    conv_id = "conv-order-check"
    m1 = CanonicalMessage.from_text("First", role=MessageRole.USER)
    m2 = CanonicalMessage.from_text("Second", role=MessageRole.USER)
    q = CanonicalMessage.from_text("Third", role=MessageRole.USER)

    key_order_1 = build_chat_cache_key(
        conversation_id=conv_id,
        history=[m1, m2],
        current_user_message=q,
    )
    key_order_2 = build_chat_cache_key(
        conversation_id=conv_id,
        history=[m2, m1],
        current_user_message=q,
    )

    assert key_order_1 != key_order_2
