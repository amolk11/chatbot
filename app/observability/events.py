"""Structured observability logging and event instrumentation."""

import logging

from app.observability.metrics import metrics

logger = logging.getLogger("app.observability.events")


def record_cache_event(
    event: str,
    conversation_id: str,
    cache_key_hash: str | None = None,
    duration_ms: float | None = None,
    error: Exception | None = None,
) -> None:
    """Log structured cache event and update metrics counters safely."""
    if event == "cache_hit":
        metrics.increment("cache_hits_total")
        logger.info(
            "Cache event: %s | conversation_id=%s | key_hash=%s | duration_ms=%s",
            event,
            conversation_id,
            cache_key_hash,
            f"{duration_ms:.2f}" if duration_ms is not None else "n/a",
        )
    elif event == "cache_miss":
        metrics.increment("cache_misses_total")
        logger.debug(
            "Cache event: %s | conversation_id=%s | key_hash=%s",
            event,
            conversation_id,
            cache_key_hash,
        )
    elif "error" in event or error is not None:
        metrics.increment("cache_errors_total")
        logger.warning(
            "Cache error event: %s | conversation_id=%s | error=%s",
            event,
            conversation_id,
            error or "Unknown cache error",
        )


def record_persistence_event(
    event: str,
    conversation_id: str,
    message_count: int | None = None,
    duration_ms: float | None = None,
    error: Exception | None = None,
) -> None:
    """Log structured database persistence event and update metrics counters safely."""
    metrics.increment("persistence_operations_total")
    if duration_ms is not None:
        metrics.record_timing("persistence_duration_ms", duration_ms)

    if error is not None:
        metrics.increment("persistence_errors_total")
        logger.error(
            "Persistence error event: %s | conversation_id=%s | error=%s",
            event,
            conversation_id,
            error,
        )
    else:
        logger.info(
            "Persistence event: %s | conversation_id=%s | msg_count=%s | duration_ms=%s",
            event,
            conversation_id,
            message_count if message_count is not None else "n/a",
            f"{duration_ms:.2f}" if duration_ms is not None else "n/a",
        )


def record_llm_event(
    event: str,
    provider: str,
    model: str,
    duration_ms: float,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    error: Exception | None = None,
) -> None:
    """Log structured LLM execution event and record token usage / latency metrics."""
    metrics.increment("llm_requests_total")
    metrics.record_timing("llm_latency_ms", duration_ms)

    if error is not None:
        metrics.increment("llm_errors_total")
        logger.error(
            "LLM failure: %s | provider=%s | model=%s | duration_ms=%.2f | error=%s",
            event,
            provider,
            model,
            duration_ms,
            error,
        )
    else:
        logger.info(
            "LLM completion: %s | provider=%s | model=%s | duration_ms=%.2f | input_tokens=%s | output_tokens=%s | total_tokens=%s",
            event,
            provider,
            model,
            duration_ms,
            input_tokens if input_tokens is not None else "n/a",
            output_tokens if output_tokens is not None else "n/a",
            total_tokens if total_tokens is not None else "n/a",
        )
