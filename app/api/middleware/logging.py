"""HTTP request logging middleware."""

import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.api.exception_handlers import unhandled_exception_handler
from app.core.logging import correlation_id_ctx
from app.observability.metrics import metrics

logger = logging.getLogger("app.api.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs HTTP request execution metrics with correlation context."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start_time = time.perf_counter()
        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""
        full_path = f"{path}?{query}" if query else path

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            status_code = response.status_code

            metrics.increment("http_requests_total")
            metrics.record_timing("http_duration_ms", duration_ms)
            if status_code >= 500:
                metrics.increment("http_request_errors_total")

            logger.info(
                "HTTP request %s %s completed with status %d in %.2fms",
                method,
                full_path,
                status_code,
                duration_ms,
                extra={
                    "extra_fields": {
                        "method": method,
                        "path": path,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "correlation_id": correlation_id_ctx.get(),
                    }
                },
            )
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            metrics.increment("http_requests_total")
            metrics.increment("http_request_errors_total")
            metrics.record_timing("http_duration_ms", duration_ms)

            logger.error(
                "HTTP request %s %s failed after %.2fms: %s",
                method,
                full_path,
                duration_ms,
                exc,
                exc_info=True,
                extra={
                    "extra_fields": {
                        "method": method,
                        "path": path,
                        "duration_ms": duration_ms,
                        "correlation_id": correlation_id_ctx.get(),
                        "error": str(exc),
                    }
                },
            )
            # Catch unhandled exceptions that escaped router handlers and return safe 500
            return await unhandled_exception_handler(request, exc)

