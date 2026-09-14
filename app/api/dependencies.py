"""FastAPI dependency injection providers for settings, LLM gateway, database, and services."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.factory import create_cache_service
from app.cache.interfaces import ICache
from app.core.config import Settings, get_settings
from app.db.interfaces import IConversationRepository
from app.db.repositories.conversation import SQLAlchemyConversationRepository
from app.db.session import get_db_session
from app.llm.factory import create_llm_service
from app.llm.interfaces import ILLMService
from app.services.chat import ChatService

__all__ = [
    "get_app_settings",
    "get_cache_service",
    "get_chat_service",
    "get_conversation_repository",
    "get_db_session",
    "get_llm_service",
]


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


def get_conversation_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IConversationRepository:
    """Dependency provider for conversation persistence repository."""
    return SQLAlchemyConversationRepository(session)


def get_cache_service(
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ICache:
    """Dependency provider for the application cache service."""
    return create_cache_service(settings)


def get_chat_service(
    llm_service: Annotated[ILLMService, Depends(get_llm_service)],
    conversation_repository: Annotated[
        IConversationRepository, Depends(get_conversation_repository)
    ],
    cache_service: Annotated[ICache, Depends(get_cache_service)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ChatService:
    """Dependency provider for the Chat orchestration application service."""
    return ChatService(
        llm_service=llm_service,
        conversation_repository=conversation_repository,
        cache=cache_service,
        cache_enabled=settings.cache_enabled,
        cache_ttl_seconds=settings.cache_ttl_seconds,
        max_history_messages=settings.chat_history_max_messages,
    )

