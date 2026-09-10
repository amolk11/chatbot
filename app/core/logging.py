"""Structured logging configuration and sensitive data redacting filters."""

import contextvars
import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings, get_settings
from app.core.constants import LogFormat

# Context variables for distributed request tracing
correlation_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)
conversation_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "conversation_id", default=None
)

# Regex patterns to scrub sensitive data from log records
SENSITIVE_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE),  # OpenAI / Generic API keys
    re.compile(r"AIza[0-9A-Za-z-_]{35}", re.IGNORECASE),  # Google API keys
    re.compile(r"lsv2_[a-z0-9_]{20,}", re.IGNORECASE),  # LangSmith API keys
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE),  # Bearer tokens
    re.compile(r"\"password\"\s*:\s*\"[^\"]+\"", re.IGNORECASE),  # JSON password fields
]


class SensitiveDataFilter(logging.Filter):
    """Logging filter that scrubs sensitive credentials and tokens from messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._redact_value(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact_value(v) for v in record.args)
        return True

    def _redact(self, text: str) -> str:
        for pattern in SENSITIVE_PATTERNS:
            text = pattern.sub("[REDACTED]", text)
        return text

    def _redact_value(self, val: Any) -> Any:
        if isinstance(val, str):
            return self._redact(val)
        return val


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production environments."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_ctx.get(),
            "conversation_id": conversation_id_ctx.get(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        extra_fields = getattr(record, "extra_fields", None)
        if isinstance(extra_fields, dict):
            log_data.update(extra_fields)

        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Clean human-readable log formatter for development environments."""

    def format(self, record: logging.LogRecord) -> str:
        corr_id = correlation_id_ctx.get()
        corr_prefix = f"[{corr_id}] " if corr_id else ""
        time_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        msg = record.getMessage()
        exc = f"\n{self.formatException(record.exc_info)}" if record.exc_info else ""
        return f"{time_str} | {record.levelname:<8} | {record.name} | {corr_prefix}{msg}{exc}"


def setup_logging(settings: Settings | None = None) -> None:
    """Initialize application logging configuration."""
    if settings is None:
        settings = get_settings()

    log_level = getattr(logging, settings.log_level.value, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if settings.log_format == LogFormat.JSON:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(ConsoleFormatter())

    console_handler.addFilter(SensitiveDataFilter())
    root_logger.addHandler(console_handler)

    # Mute noisy third-party loggers
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = True
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
