"""Correlation and request tracing middleware."""

import re
import uuid
from typing import Final

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import correlation_id_ctx

CORRELATION_ID_HEADER: Final[str] = "X-Correlation-ID"
MAX_CORRELATION_ID_LENGTH: Final[int] = 64
CORRELATION_ID_REGEX: Final[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9_\-\.]{1,64}$")


def is_valid_correlation_id(correlation_id: str | None) -> bool:
    """Validate correlation ID to avoid injection or malicious characters."""
    if not correlation_id:
        return False
    if len(correlation_id) > MAX_CORRELATION_ID_LENGTH:
        return False
    return bool(CORRELATION_ID_REGEX.match(correlation_id))


def generate_correlation_id() -> str:
    """Generate a standard UUID4-based correlation ID."""
    return str(uuid.uuid4())


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns or validates a correlation ID for every HTTP request."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        incoming_id = request.headers.get(CORRELATION_ID_HEADER)

        if is_valid_correlation_id(incoming_id) and incoming_id is not None:
            correlation_id = incoming_id
        else:
            correlation_id = generate_correlation_id()

        # Set context variable for logging and trace context
        token = correlation_id_ctx.set(correlation_id)
        request.state.correlation_id = correlation_id

        try:
            response = await call_next(request)
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            return response
        finally:
            correlation_id_ctx.reset(token)
