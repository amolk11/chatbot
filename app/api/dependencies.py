"""FastAPI dependency injection providers."""

from app.core.config import Settings, get_settings


def get_app_settings() -> Settings:
    """Dependency provider for application settings."""
    return get_settings()
