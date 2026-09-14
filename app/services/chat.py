"""Chat orchestration service executing LangGraph workflows with injected LLM services."""

import logging
from typing import TYPE_CHECKING

from app.core.exceptions import ValidationError
from app.domain.messages import CanonicalMessage, MessageRole
from app.graph.chatbot import build_chat_graph
from app.llm.interfaces import ILLMService

if TYPE_CHECKING:
    from app.graph.state import ChatGraphState

logger = logging.getLogger("app.services.chat")


class ChatService:
    """Application service for orchestrating single-turn conversational interactions."""

    def __init__(self, llm_service: ILLMService) -> None:
        self._llm_service = llm_service
        self._graph = build_chat_graph(llm_service)

    async def process_message(
        self,
        message: str,
        conversation_id: str | None = None,
    ) -> CanonicalMessage:
        """Execute chat interaction through the LangGraph workflow.

        Args:
            message: User input text string.
            conversation_id: Optional conversation identifier (stateless in Phase 3).

        Returns:
            CanonicalMessage containing the assistant's reply.

        Raises:
            ValidationError: If input validation fails.
            LLMError: If downstream LLM generation fails.
        """
        if not message or not message.strip():
            raise ValidationError("Chat input message cannot be empty or whitespace.")

        user_message = CanonicalMessage.from_text(
            text=message.strip(),
            role=MessageRole.USER,
        )

        initial_state: ChatGraphState = {
            "messages": [user_message],
            "response": None,
            "error": None,
        }

        logger.info(
            "Executing chat workflow for message id=%s (conversation_id=%s)",
            user_message.id,
            conversation_id,
        )

        result_state = await self._graph.ainvoke(initial_state)

        assistant_response: CanonicalMessage | None = result_state.get("response")
        if assistant_response is None:
            logger.error("Chat graph execution returned null response state for message id=%s", user_message.id)
            raise ValidationError("Workflow execution completed without producing an assistant response.")

        logger.info(
            "Chat workflow completed successfully. Produced response id=%s",
            assistant_response.id,
        )
        return assistant_response
