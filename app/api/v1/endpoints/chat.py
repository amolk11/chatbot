"""Chat interaction endpoint definitions."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_chat_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService

router = APIRouter(tags=["Chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Chat Turn",
    description="Processes a user conversation turn via LangGraph, loaded conversation history, and the configured LLM provider.",
)
async def execute_chat_turn(
    request: ChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    """Execute single-turn chat interaction with persistent conversation history."""
    assistant_message, active_conversation_id = await chat_service.process_message(
        message=request.message,
        conversation_id=request.conversation_id,
    )

    return ChatResponse(
        message=assistant_message,
        conversation_id=active_conversation_id,
    )
