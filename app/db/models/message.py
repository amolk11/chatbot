"""Message database ORM model."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.conversation import ConversationModel


class MessageModel(Base):
    """Database model representing a persisted conversation turn message."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Unique UUID message identifier",
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key reference to parent conversation",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Message author role: system, user, or assistant",
    )
    content_type: Mapped[str] = mapped_column(
        String(20),
        default="text",
        nullable=False,
        doc="Primary content modality descriptor",
    )
    content: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        doc="Serialized JSON list of content blocks",
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Monotonically increasing sequence integer for deterministic chronological ordering",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        doc="UTC timestamp when the message was recorded",
    )

    # Relationships
    conversation: Mapped["ConversationModel"] = relationship(
        "ConversationModel",
        back_populates="messages",
    )

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "sequence_number",
            name="uq_messages_conversation_sequence",
        ),
        Index(
            "ix_messages_conversation_sequence",
            "conversation_id",
            "sequence_number",
        ),
    )
