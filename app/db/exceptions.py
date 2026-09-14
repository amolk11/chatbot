"""Database and persistence layer exception definitions."""

from typing import Any

from app.core.exceptions import ChatbotError


class PersistenceError(ChatbotError):
    """Base exception for persistence and database access errors."""

    def __init__(
        self,
        message: str = "A database persistence error occurred.",
        code: str = "PERSISTENCE_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=status_code, details=details)


class ConversationNotFoundError(PersistenceError):
    """Raised when a requested conversation session does not exist."""

    def __init__(
        self,
        message: str = "Conversation not found.",
        conversation_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged_details = details or {}
        if conversation_id:
            merged_details["conversation_id"] = conversation_id
        super().__init__(
            message=message,
            code="CONVERSATION_NOT_FOUND",
            status_code=404,
            details=merged_details,
        )


class PersistenceConfigurationError(PersistenceError):
    """Raised when database connection string or engine configuration is invalid."""

    def __init__(
        self,
        message: str = "Database configuration is invalid.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="PERSISTENCE_CONFIGURATION_ERROR",
            status_code=500,
            details=details,
        )
