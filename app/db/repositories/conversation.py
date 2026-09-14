"""SQLAlchemy implementation of the conversation repository port."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.exceptions import ConversationNotFoundError, PersistenceError
from app.db.models.conversation import ConversationModel
from app.db.models.message import MessageModel
from app.domain.messages import CanonicalMessage, MessageRole, TextContentBlock

logger = logging.getLogger("app.db.repository.conversation")


class SQLAlchemyConversationRepository:
    """SQLAlchemy 2.x async repository for conversation and message persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def conversation_exists(self, conversation_id: str) -> bool:
        """Check if a conversation session exists."""
        try:
            stmt = select(exists().where(ConversationModel.id == conversation_id))
            result = await self._session.execute(stmt)
            return bool(result.scalar())
        except Exception as exc:
            logger.error("Failed to check existence of conversation %s: %s", conversation_id, exc)
            raise PersistenceError(f"Failed to query conversation existence: {exc}") from exc

    async def create_conversation(self, conversation_id: str | None = None) -> str:
        """Create a new conversation session record."""
        conv_id = conversation_id or str(uuid.uuid4())
        try:
            conv = ConversationModel(
                id=conv_id,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self._session.add(conv)
            await self._session.flush()
            logger.debug("Created conversation record id=%s", conv_id)
            return conv_id
        except Exception as exc:
            logger.error("Failed to create conversation %s: %s", conv_id, exc)
            raise PersistenceError(f"Failed to create conversation record: {exc}") from exc

    async def get_history(
        self,
        conversation_id: str,
        *,
        limit: int = 50,
    ) -> list[CanonicalMessage]:
        """Fetch chronological message history up to limit messages."""
        try:
            # Query the latest `limit` messages in descending sequence order, then reverse to chronological
            stmt = (
                select(MessageModel)
                .where(MessageModel.conversation_id == conversation_id)
                .order_by(MessageModel.sequence_number.desc())
                .limit(limit)
            )
            result = await self._session.execute(stmt)
            models = list(result.scalars().all())

            # Reverse to ensure chronological order (oldest to newest)
            models.reverse()

            canonical_messages: list[CanonicalMessage] = []
            for msg_model in models:
                raw_content: list[dict[str, Any]] = msg_model.content or []
                content_blocks = [
                    TextContentBlock.model_validate(block_data)
                    for block_data in raw_content
                ]
                canonical_messages.append(
                    CanonicalMessage(
                        id=msg_model.id,
                        role=MessageRole(msg_model.role),
                        content=content_blocks,
                        created_at=msg_model.created_at,
                    )
                )

            logger.debug(
                "Loaded %d historical messages for conversation id=%s",
                len(canonical_messages),
                conversation_id,
            )
            return canonical_messages
        except Exception as exc:
            logger.error("Failed to load history for conversation %s: %s", conversation_id, exc)
            raise PersistenceError(f"Failed to retrieve conversation history: {exc}") from exc

    async def persist_turn(
        self,
        conversation_id: str,
        user_message: CanonicalMessage,
        assistant_message: CanonicalMessage,
    ) -> None:
        """Atomically persist user and assistant messages for a successful turn."""
        try:
            # Ensure conversation exists or create it
            conv = await self._session.get(ConversationModel, conversation_id)
            now = datetime.now(UTC)

            if conv is None:
                conv = ConversationModel(
                    id=conversation_id,
                    created_at=now,
                    updated_at=now,
                )
                self._session.add(conv)
                await self._session.flush()

            # Find maximum sequence number in conversation
            stmt = select(func.max(MessageModel.sequence_number)).where(
                MessageModel.conversation_id == conversation_id
            )
            seq_result = await self._session.execute(stmt)
            max_seq: int = seq_result.scalar() or 0

            # Create User message model
            user_model = MessageModel(
                id=user_message.id,
                conversation_id=conversation_id,
                role=user_message.role.value,
                content_type="text",
                content=[block.model_dump() for block in user_message.content],
                sequence_number=max_seq + 1,
                created_at=user_message.created_at,
            )

            # Create Assistant message model
            assistant_model = MessageModel(
                id=assistant_message.id,
                conversation_id=conversation_id,
                role=assistant_message.role.value,
                content_type="text",
                content=[block.model_dump() for block in assistant_message.content],
                sequence_number=max_seq + 2,
                created_at=assistant_message.created_at,
            )

            # Update conversation updated_at timestamp
            conv.updated_at = now

            self._session.add_all([user_model, assistant_model])
            await self._session.flush()

            logger.info(
                "Persisted chat turn for conversation id=%s (sequences %d, %d)",
                conversation_id,
                user_model.sequence_number,
                assistant_model.sequence_number,
            )
        except ConversationNotFoundError:
            raise
        except Exception as exc:
            logger.error("Failed to persist turn for conversation %s: %s", conversation_id, exc)
            raise PersistenceError(f"Failed to persist chat turn: {exc}") from exc
