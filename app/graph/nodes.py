"""LangGraph node implementations for validation, generation, and response formatting."""

import logging
from typing import Any

from app.core.exceptions import ValidationError
from app.graph.state import ChatGraphState
from app.llm.interfaces import ILLMService

logger = logging.getLogger("app.graph.nodes")


def validate_node(state: ChatGraphState) -> dict[str, Any]:
    """Validate graph execution state and message integrity."""
    messages = state.get("messages", [])
    if not messages:
        raise ValidationError("Chat graph received empty message sequence.")

    last_message = messages[-1]
    if not last_message.text.strip():
        raise ValidationError("Last user message in sequence contains empty text content.")

    logger.debug("Validation node passed with %d messages in state", len(messages))
    return {}


class GenerateNode:
    """Callable class executing generation with an injected ILLMService instance."""

    def __init__(self, llm_service: ILLMService) -> None:
        self.llm_service = llm_service

    async def __call__(self, state: ChatGraphState) -> dict[str, Any]:
        messages = state["messages"]
        logger.debug("Generate node invoking ILLMService with %d messages", len(messages))
        assistant_message = await self.llm_service.generate(messages)
        return {"response": assistant_message}


def format_node(state: ChatGraphState) -> dict[str, Any]:
    """Format and normalize the assistant response in graph state."""
    response = state.get("response")
    if response is None:
        raise ValidationError("Generation step produced no assistant response.")

    logger.debug("Format node completed for response id=%s", response.id)
    return {"response": response}
