"""FastAPI dependency injection providers for settings, LLM gateway, and services."""

from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.llm.factory import create_llm_service
from app.llm.interfaces import ILLMService
from app.services.chat import ChatService


def get_app_settings(request: Request) -> Settings:
    """Dependency provider for application settings, isolated via request app state."""
    if hasattr(request.app.state, "settings") and request.app.state.settings is not None:
        settings: Settings = request.app.state.settings
        return settings
    return get_settings()


def get_llm_service(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ILLMService:
    """Dependency provider for the LLM Gateway service."""
    return create_llm_service(settings)


def get_chat_service(
    llm_service: Annotated[ILLMService, Depends(get_llm_service)],
) -> ChatService:
    """Dependency provider for the Chat orchestration application service."""
    return ChatService(llm_service=llm_service)
