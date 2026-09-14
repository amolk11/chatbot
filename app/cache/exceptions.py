"""Cache-specific exception definitions."""

from app.core.exceptions import AppException


class CacheError(AppException):
    """Base exception for all caching-related failures."""

    def __init__(
        self,
        message: str = "A caching error occurred.",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="CACHE_ERROR",
            status_code=500,
            details=details,
        )


class CacheConnectionError(CacheError):
    """Raised when connecting or communicating with the cache backend fails."""

    def __init__(
        self,
        message: str = "Failed to establish or maintain connection with cache backend.",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)
        self.error_code = "CACHE_CONNECTION_ERROR"


class CacheSerializationError(CacheError):
    """Raised when serializing or deserializing cached data fails."""

    def __init__(
        self,
        message: str = "Failed to serialize or deserialize cached content.",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)
        self.error_code = "CACHE_SERIALIZATION_ERROR"
