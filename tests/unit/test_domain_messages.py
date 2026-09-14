"""Unit tests for canonical message domain entities and content blocks."""

from datetime import UTC, datetime

from app.domain.messages import (
    CanonicalMessage,
    ContentType,
    MessageRole,
    TextContentBlock,
)


def test_text_content_block_initialization() -> None:
    """Verify TextContentBlock fields and default discriminator."""
    block = TextContentBlock(text="Hello world")
    assert block.type == ContentType.TEXT
    assert block.text == "Hello world"


def test_canonical_message_from_text() -> None:
    """Verify factory method builds valid user CanonicalMessage."""
    msg = CanonicalMessage.from_text("Explain quantum computing")

    assert msg.role == MessageRole.USER
    assert len(msg.content) == 1
    assert msg.content[0].type == ContentType.TEXT
    assert msg.text == "Explain quantum computing"
    assert msg.id is not None
    assert isinstance(msg.created_at, datetime)
    assert msg.created_at.tzinfo == UTC


def test_canonical_message_roles() -> None:
    """Verify CanonicalMessage support for system and assistant roles."""
    sys_msg = CanonicalMessage.from_text("System instructions", role=MessageRole.SYSTEM)
    assert sys_msg.role == MessageRole.SYSTEM

    asst_msg = CanonicalMessage.from_text("Assistant response", role=MessageRole.ASSISTANT)
    assert asst_msg.role == MessageRole.ASSISTANT


def test_canonical_message_serialization() -> None:
    """Verify model serialization to dictionary and JSON."""
    msg = CanonicalMessage.from_text("Test message", role=MessageRole.USER, message_id="msg-123")
    data = msg.model_dump()

    assert data["id"] == "msg-123"
    assert data["role"] == "user"
    assert data["content"] == [{"type": "text", "text": "Test message"}]
