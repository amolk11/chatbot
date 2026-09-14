"""Persistence port interfaces defining conversation storage operations."""

from typing import Protocol, runtime_checkable

from app.domain.messages import CanonicalMessage


@runtime_checkable
class IConversationRepository(Protocol):
    """Abstract repository port defining conversation and message persistence operations."""

    async def conversation_exists(self, conversation_id: str) -> bool:
        """Determine if a conversation session exists in persistent storage."""
        ...

    async def create_conversation(self, conversation_id: str | None = None) -> str:
        """Create and persist a new conversation session, returning its unique identifier."""
        ...

    async def get_history(
        self,
        conversation_id: str,
        *,
        limit: int = 50,
    ) -> list[CanonicalMessage]:
        """Retrieve historical canonical messages for a conversation ordered chronologically."""
        ...

    async def persist_turn(
        self,
        conversation_id: str,
        user_message: CanonicalMessage,
        assistant_message: CanonicalMessage,
    ) -> None:
        """Atomically persist a complete conversation turn (user + assistant) in a single transaction."""
        ...
