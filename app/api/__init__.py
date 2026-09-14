"""API layer containing endpoints, middleware, and dependencies."""

from app.api.dependencies import get_app_settings

__all__ = ["get_app_settings"]
