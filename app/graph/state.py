"""LangGraph state definitions for conversational workflows."""

from typing import TypedDict

from app.domain.messages import CanonicalMessage


class ChatGraphState(TypedDict):
    """Execution state container passed through the LangGraph chatbot pipeline."""

    messages: list[CanonicalMessage]
    response: CanonicalMessage | None
    error: str | None
