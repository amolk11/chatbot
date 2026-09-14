"""Global FastAPI exception handlers conforming to standard error response schemas."""

import logging
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import ChatbotError
from app.core.logging import correlation_id_ctx
from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger("app.api.exceptions")


def format_validation_errors(raw_errors: Sequence[Any]) -> list[dict[str, Any]]:
    """Sanitize and format Pydantic validation errors for API consumers."""
    formatted: list[dict[str, Any]] = []
    for err in raw_errors:
        loc = " -> ".join(str(item) for item in err.get("loc", []))
        formatted.append(
            {
                "field": loc,
                "message": err.get("msg", "Validation error"),
                "type": err.get("type", "value_error"),
            }
        )
    return formatted


async def chatbot_error_handler(request: Request, exc: ChatbotError) -> JSONResponse:
    """Handle domain and application-specific exceptions."""
    correlation_id = getattr(request.state, "correlation_id", None) or correlation_id_ctx.get()

    logger.warning(
        "Handled application exception [%s]: %s (status=%d, correlation_id=%s)",
        exc.code,
        exc.message,
        exc.status_code,
        correlation_id,
        extra={"extra_fields": {"code": exc.code, "details": exc.details}},
    )

    error_payload = ErrorResponse(
        error=ErrorDetail(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
            details=exc.details if exc.details else None,
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload.model_dump(exclude_none=True),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI and Pydantic request validation exceptions."""
    correlation_id = getattr(request.state, "correlation_id", None) or correlation_id_ctx.get()
    sanitized_errors = format_validation_errors(exc.errors())

    logger.info(
        "Request validation failed on %s %s (correlation_id=%s): %s",
        request.method,
        request.url.path,
        correlation_id,
        sanitized_errors,
    )

    error_payload = ErrorResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="Request input validation failed. Check 'details' for field-level errors.",
            correlation_id=correlation_id,
            details=sanitized_errors,
        )
    )
    return JSONResponse(
        status_code=422,
        content=error_payload.model_dump(exclude_none=True),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle Starlette and FastAPI HTTP exceptions (e.g. 404, 405)."""
    correlation_id = getattr(request.state, "correlation_id", None) or correlation_id_ctx.get()

    error_code = f"HTTP_{exc.status_code}"
    error_payload = ErrorResponse(
        error=ErrorDetail(
            code=error_code,
            message=str(exc.detail) if exc.detail else "HTTP error encountered.",
            correlation_id=correlation_id,
        )
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload.model_dump(exclude_none=True),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unhandled server exceptions (HTTP 500)."""
    correlation_id = getattr(request.state, "correlation_id", None) or correlation_id_ctx.get()

    logger.error(
        "Unhandled server error on %s %s: %s (correlation_id=%s)",
        request.method,
        request.url.path,
        exc,
        correlation_id,
        exc_info=True,
    )

    # Never leak internal exception messages or tracebacks to the client in responses
    error_payload = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred. Please contact support with the correlation ID.",
            correlation_id=correlation_id,
        )
    )
    return JSONResponse(
        status_code=500,
        content=error_payload.model_dump(exclude_none=True),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all standard exception handlers with the FastAPI application instance."""
    app.add_exception_handler(ChatbotError, chatbot_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
