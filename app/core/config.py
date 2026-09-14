"""Application configuration management using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import AppEnvironment, LogFormat, LogLevel


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # General App Settings
    app_name: str = Field(default="AI Chatbot", description="Name of the application")
    app_version: str = Field(default="0.1.0", description="Application semantic version")
    app_env: AppEnvironment = Field(
        default=AppEnvironment.DEVELOPMENT,
        description="Application environment: development, testing, production",
    )
    api_v1_prefix: str = Field(default="/api/v1", description="Prefix for API v1 routes")
    cors_origins: list[str] = Field(
        default=["*"],
        description="List of allowed CORS origins",
    )

    # Logging Settings
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Application log level")
    log_format: LogFormat = Field(
        default=LogFormat.CONSOLE,
        description="Logging format: console (human-readable) or json (production)",
    )

    # LLM Settings
    llm_provider: str | None = Field(
        default=None,
        description="LLM provider: openai, anthropic, google, or mock",
    )
    llm_model: str | None = Field(
        default=None,
        description="Model name/identifier",
    )
    llm_api_key: SecretStr | None = Field(
        default=None,
        description="Primary LLM provider API key",
    )

    # Persistence Settings (Phase 4)
    database_url: str = Field(
        default="sqlite+aiosqlite:///./chatbot.db",
        description="Database connection URL (e.g. sqlite+aiosqlite:///./chatbot.db or postgresql+asyncpg://...)",
    )
    chat_history_max_messages: int = Field(
        default=50,
        description="Maximum number of historical conversation messages to load for context",
    )

    # Observability & LangSmith Settings (Placeholders for Future Phase 6)
    langsmith_tracing: bool = Field(
        default=False,
        description="Enable LangSmith distributed tracing",
    )
    langsmith_api_key: SecretStr | None = Field(
        default=None,
        description="LangSmith API key",
    )
    langsmith_project: str | None = Field(
        default="chatbot-dev",
        description="LangSmith project name",
    )

    # Caching Settings (Placeholders for Future Phase 5)
    redis_url: str | None = Field(
        default=None,
        description="Redis connection URL (e.g. redis://localhost:6379/0)",
    )

    # Rate Limiting & Security (Future Phase 8)
    rate_limit_per_minute: int = Field(
        default=60,
        description="Maximum allowed requests per minute per client IP/Key",
    )

    @property
    def is_development(self) -> bool:
        """Check if current environment is development."""
        return self.app_env == AppEnvironment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        """Check if current environment is testing."""
        return self.app_env == AppEnvironment.TESTING

    @property
    def is_production(self) -> bool:
        """Check if current environment is production."""
        return self.app_env == AppEnvironment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    """Factory function for cached application settings instance."""
    return Settings()
