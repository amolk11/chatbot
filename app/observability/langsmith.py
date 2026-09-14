"""LangSmith distributed tracing initialization and lifecycle integration."""

import logging
import os

from app.core.config import Settings

logger = logging.getLogger("app.observability.langsmith")


def setup_langsmith(settings: Settings) -> None:
    """Configure LangSmith environment variables based on application settings.

    Ensures that tracing is strictly non-fatal: missing keys or disabled settings
    guarantee zero network telemetry calls without disrupting application runtime.

    Args:
        settings: Application settings containing LangSmith configurations.
    """
    if settings.langsmith_tracing and settings.langsmith_api_key is not None:
        api_key = settings.langsmith_api_key.get_secret_value()
        project = settings.langsmith_project or "chatbot-dev"
        endpoint = settings.langsmith_endpoint or "https://api.smith.langchain.com"

        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_API_KEY"] = api_key
        os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGSMITH_PROJECT"] = project
        os.environ["LANGCHAIN_PROJECT"] = project
        os.environ["LANGSMITH_ENDPOINT"] = endpoint
        os.environ["LANGCHAIN_ENDPOINT"] = endpoint

        logger.info(
            "LangSmith distributed tracing enabled for project '%s' at endpoint '%s'",
            project,
            endpoint,
        )
    else:
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        os.environ.pop("LANGSMITH_API_KEY", None)
        os.environ.pop("LANGCHAIN_API_KEY", None)
        logger.debug("LangSmith distributed tracing is disabled")
