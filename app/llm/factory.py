"""LLM service factory provider."""

import logging

from app.core.config import Settings, get_settings
from app.llm.exceptions import LLMConfigurationError
from app.llm.interfaces import ILLMService
from app.llm.mock import MockLLMService
from app.llm.providers.openai import OpenAILLMService

logger = logging.getLogger("app.llm.factory")


def create_llm_service(settings: Settings | None = None) -> ILLMService:
    """Create and configure an ILLMService instance based on application settings."""
    app_settings = settings or get_settings()

    provider = (app_settings.llm_provider or "mock").lower().strip()

    if app_settings.is_testing or provider == "mock":
        logger.info("Initializing MockLLMService (provider=%s)", provider)
        return MockLLMService()

    if provider == "openai":
        if not app_settings.llm_api_key:
            raise LLMConfigurationError(
                "LLM_API_KEY must be configured when LLM_PROVIDER is 'openai'."
            )
        model = app_settings.llm_model or "gpt-4o-mini"
        logger.info("Initializing OpenAILLMService with model %s", model)
        return OpenAILLMService(
            api_key=app_settings.llm_api_key.get_secret_value(),
            model=model,
        )

    raise LLMConfigurationError(
        f"Unsupported LLM provider '{provider}'. Supported providers in Phase 3: 'openai', 'mock'."
    )
