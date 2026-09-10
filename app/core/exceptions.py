"""Core exception hierarchy for the AI Chatbot application."""

from typing import Any, Dict, Optional


class ChatbotError(Exception):
    """Base exception class for all application errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation for API responses."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class ConfigurationError(ChatbotError):
    """Raised when an invalid configuration is detected."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=500,
            details=details,
        )


class ValidationError(ChatbotError):
    """Raised when input validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class ResourceNotFoundError(ChatbotError):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=404,
            details=details,
        )


class ExternalServiceError(ChatbotError):
    """Raised when an external service or provider fails."""

    def __init__(
        self,
        message: str,
        code: str = "EXTERNAL_SERVICE_ERROR",
        status_code: int = 502,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )
