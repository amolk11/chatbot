"""Pydantic request and response schemas for the Chat API."""

from pydantic import BaseModel, Field

from app.domain.messages import CanonicalMessage


class ChatRequest(BaseModel):
    """Payload schema for initiating a chatbot interaction."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User text input to process.",
        examples=["Hello! What can you help me with?"],
    )
    conversation_id: str | None = Field(
        default=None,
        description="Optional conversation identifier (stateless in Phase 3; reserved for future persistence).",
        examples=["conv_123456789"],
    )


class ChatResponse(BaseModel):
    """Standardized response schema returned by the Chat API."""

    message: CanonicalMessage = Field(..., description="Canonical assistant reply message.")
    conversation_id: str | None = Field(
        default=None,
        description="Associated conversation identifier.",
    )
