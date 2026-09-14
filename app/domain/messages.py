"""Canonical message domain models supporting future multimodal extensibility."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, computed_field


class MessageRole(StrEnum):
    """Supported roles in a conversation exchange."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ContentType(StrEnum):
    """Supported content block modalities."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    FILE = "file"


class BaseContentBlock(BaseModel):
    """Abstract base class for all content block types."""

    type: ContentType


class TextContentBlock(BaseContentBlock):
    """Text-based content block."""

    type: Literal[ContentType.TEXT] = ContentType.TEXT
    text: str = Field(..., min_length=1, description="Textual content payload")


# Content block type union (ready for future multimodal expansion with ImageContentBlock, etc.)
ContentBlock = Annotated[
    TextContentBlock,
    Field(discriminator="type"),
]


class CanonicalMessage(BaseModel):
    """Canonical domain representation of a conversation message."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique message identifier",
    )
    role: MessageRole = Field(..., description="Role of the message author")
    content: list[TextContentBlock] = Field(
        ...,
        min_length=1,
        description="List of content blocks comprising the message",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the message was created",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def text(self) -> str:
        """Extract and concatenate all text content blocks."""
        return "".join(block.text for block in self.content if isinstance(block, TextContentBlock))

    @classmethod
    def from_text(
        cls,
        text: str,
        role: MessageRole = MessageRole.USER,
        message_id: str | None = None,
    ) -> "CanonicalMessage":
        """Factory helper to build a CanonicalMessage from a raw string."""
        return cls(
            id=message_id or str(uuid.uuid4()),
            role=role,
            content=[TextContentBlock(text=text)],
        )
