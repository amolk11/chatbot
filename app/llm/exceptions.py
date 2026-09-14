"""LLM Gateway exception hierarchy."""

from typing import Any

from app.core.exceptions import ChatbotError


class LLMError(ChatbotError):
    """Base exception for all LLM Gateway errors."""

    def __init__(
        self,
        message: str,
        code: str = "LLM_ERROR",
        status_code: int = 502,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code, details=details)


class LLMConfigurationError(LLMError):
    """Raised when LLM provider settings or credentials are misconfigured."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="LLM_CONFIGURATION_ERROR",
            status_code=500,
            details=details,
        )


class LLMProviderError(LLMError):
    """Raised when an external LLM provider fails (e.g. rate limit, 5xx, auth failure)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="LLM_PROVIDER_ERROR",
            status_code=502,
            details=details,
        )


class LLMTimeoutError(LLMError):
    """Raised when an LLM provider request exceeds the configured timeout."""

    def __init__(
        self,
        message: str = "LLM provider request timed out.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="LLM_TIMEOUT_ERROR",
            status_code=504,
            details=details,
        )


class LLMResponseParsingError(LLMError):
    """Raised when the LLM provider returns an unparseable or empty response."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="LLM_RESPONSE_PARSING_ERROR",
            status_code=502,
            details=details,
        )
