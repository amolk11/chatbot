"""FastAPI application entry point and factory."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.core.config import Settings, get_settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for application startup and shutdown events."""
    settings = getattr(app.state, "settings", get_settings())
    setup_logging(settings)
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory for the AI Chatbot FastAPI service."""
    app_settings = settings or get_settings()

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        docs_url="/docs" if app_settings.is_development else None,
        redoc_url="/redoc" if app_settings.is_development else None,
        openapi_url="/openapi.json" if app_settings.is_development else None,
        lifespan=lifespan,
    )

    app.state.settings = app_settings

    return app


app = create_app()
