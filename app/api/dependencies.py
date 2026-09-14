"""FastAPI dependency injection providers."""

from fastapi import Request

from app.core.config import Settings, get_settings


def get_app_settings(request: Request) -> Settings:
    """Dependency provider for application settings, isolated via request app state."""
    if hasattr(request.app.state, "settings") and request.app.state.settings is not None:
        settings: Settings = request.app.state.settings
        return settings
    return get_settings()
