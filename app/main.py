"""FastAPI application entry point, factory, lifespan, and router registration."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import register_exception_handlers
from app.api.middleware.correlation import CorrelationIdMiddleware
from app.api.middleware.logging import RequestLoggingMiddleware
from app.api.v1.endpoints import health
from app.api.v1.router import api_v1_router
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for application startup and shutdown events."""
    settings: Settings = getattr(app.state, "settings", get_settings())
    setup_logging(settings)
    # Future Phase: Initialize database connection pools, Redis clients, LLM services
    yield
    # Future Phase: Graceful teardown of connections and async task queues


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory for the AI Chatbot FastAPI service."""
    app_settings = settings or get_settings()

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description="Production-oriented modular AI Chatbot backend service.",
        docs_url="/docs" if app_settings.is_development else None,
        redoc_url="/redoc" if app_settings.is_development else None,
        openapi_url="/openapi.json" if app_settings.is_development else None,
        lifespan=lifespan,
    )

    # Store settings in application state for dependency access
    app.state.settings = app_settings

    # Register Exception Handlers
    register_exception_handlers(app)

    # Register Middleware (Note: Added in reverse execution order)
    # 1. Request logging (inner)
    app.add_middleware(RequestLoggingMiddleware)
    # 2. Correlation ID injection & propagation
    app.add_middleware(CorrelationIdMiddleware)
    # 3. Cross-Origin Resource Sharing (outer)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    # Register Root Health Endpoints (Accessible at /health and /health/ready)
    app.include_router(health.router)

    # Register Versioned API v1 Router (e.g., /api/v1/...)
    app.include_router(api_v1_router, prefix=app_settings.api_v1_prefix)

    return app


# Default ASGI application instance for Uvicorn
app = create_app()
