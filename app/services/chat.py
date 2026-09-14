"""Chat orchestration service executing LangGraph workflows with persisted conversation history."""

import logging
import uuid
from typing import TYPE_CHECKING

from app.core.exceptions import ValidationError
from app.db.exceptions import ConversationNotFoundError
from app.db.interfaces import IConversationRepository
from app.domain.messages import CanonicalMessage, MessageRole
from app.graph.chatbot import build_chat_graph
from app.llm.interfaces import ILLMService

if TYPE_CHECKING:
    from app.graph.state import ChatGraphState

logger = logging.getLogger("app.services.chat")


class ChatService:
    """Application service for orchestrating conversational interactions with durable history."""

    def __init__(
        self,
        llm_service: ILLMService,
        conversation_repository: IConversationRepository,
        max_history_messages: int = 50,
    ) -> None:
        self._llm_service = llm_service
        self._repository = conversation_repository
        self._max_history_messages = max_history_messages
        self._graph = build_chat_graph(llm_service)

    async def process_message(
        self,
        message: str,
        conversation_id: str | None = None,
    ) -> tuple[CanonicalMessage, str]:
        """Execute chat interaction through historical context loading and LangGraph workflow.

        Args:
            message: User input text string.
            conversation_id: Optional existing conversation identifier.

        Returns:
            Tuple of (CanonicalMessage response, active conversation_id).

        Raises:
            ValidationError: If input message validation fails.
            ConversationNotFoundError: If supplied conversation_id does not exist.
            LLMError: If downstream LLM generation fails.
            PersistenceError: If database operations fail.
        """
        if not message or not message.strip():
            raise ValidationError("Chat input message cannot be empty or whitespace.")

        # 1. Resolve active conversation ID and load existing chronological history
        if conversation_id:
            exists = await self._repository.conversation_exists(conversation_id)
            if not exists:
                logger.warning("Conversation %s requested but does not exist", conversation_id)
                raise ConversationNotFoundError(
                    message=f"Conversation '{conversation_id}' was not found.",
                    conversation_id=conversation_id,
                )
            active_conv_id = conversation_id
            history = await self._repository.get_history(
                active_conv_id,
                limit=self._max_history_messages,
            )
        else:
            active_conv_id = str(uuid.uuid4())
            history = []

        # 2. Construct canonical user message
        user_message = CanonicalMessage.from_text(
            text=message.strip(),
            role=MessageRole.USER,
        )

        # 3. Assemble full conversational context: historical turns + current user message
        graph_messages = [*history, user_message]

        initial_state: ChatGraphState = {
            "messages": graph_messages,
            "response": None,
            "error": None,
        }

        logger.info(
            "Executing chat workflow for message id=%s in conversation id=%s (history_len=%d)",
            user_message.id,
            active_conv_id,
            len(history),
        )

        # 4. Invoke LangGraph workflow
        result_state = await self._graph.ainvoke(initial_state)

        assistant_response: CanonicalMessage | None = result_state.get("response")
        if assistant_response is None:
            logger.error(
                "Chat graph execution returned null response state for message id=%s",
                user_message.id,
            )
            raise ValidationError(
                "Workflow execution completed without producing an assistant response."
            )

        # 5. Persist the turn atomically (user + assistant)
        await self._repository.persist_turn(
            conversation_id=active_conv_id,
            user_message=user_message,
            assistant_message=assistant_response,
        )

        logger.info(
            "Chat workflow and turn persistence completed successfully for conversation id=%s",
            active_conv_id,
        )
        return assistant_response, active_conv_id
