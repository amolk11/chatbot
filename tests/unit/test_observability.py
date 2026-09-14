"""Unit and integration tests for Phase 6 Observability, LangSmith, and Metrics."""

import os
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from app.cache.memory import InMemoryCache
from app.core.config import Settings
from app.db.repositories.conversation import SQLAlchemyConversationRepository
from app.domain.messages import CanonicalMessage, MessageRole
from app.llm.mock import MockLLMService
from app.llm.providers.openai import OpenAILLMService
from app.observability.events import (
    record_cache_event,
    record_llm_event,
    record_persistence_event,
)
from app.observability.langsmith import setup_langsmith
from app.observability.metrics import MetricsCollector, metrics
from app.observability.tracing import build_langgraph_trace_config
from app.services.chat import ChatService



def test_setup_langsmith_enabled() -> None:
    """Verify setup_langsmith accurately configures environment variables when enabled."""
    settings = Settings(
        langsmith_tracing=True,
        langsmith_api_key=SecretStr("lsv2_pt_test_secret_key_12345"),
        langsmith_project="test-project-phase6",
        langsmith_endpoint="https://custom.smith.endpoint.com",
    )
    setup_langsmith(settings)

    assert os.environ.get("LANGSMITH_TRACING") == "true"
    assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
    assert os.environ.get("LANGSMITH_API_KEY") == "lsv2_pt_test_secret_key_12345"
    assert os.environ.get("LANGCHAIN_API_KEY") == "lsv2_pt_test_secret_key_12345"
    assert os.environ.get("LANGSMITH_PROJECT") == "test-project-phase6"
    assert os.environ.get("LANGSMITH_ENDPOINT") == "https://custom.smith.endpoint.com"

    # Reset environment back to disabled state
    disabled_settings = Settings(langsmith_tracing=False)
    setup_langsmith(disabled_settings)


def test_setup_langsmith_disabled() -> None:
    """Verify setup_langsmith disables tracing flags and removes API keys from environment."""
    # First seed dummy values
    os.environ["LANGSMITH_API_KEY"] = "dummy"
    os.environ["LANGCHAIN_API_KEY"] = "dummy"

    settings = Settings(langsmith_tracing=False, langsmith_api_key=None)
    setup_langsmith(settings)

    assert os.environ.get("LANGSMITH_TRACING") == "false"
    assert os.environ.get("LANGCHAIN_TRACING_V2") == "false"
    assert "LANGSMITH_API_KEY" not in os.environ
    assert "LANGCHAIN_API_KEY" not in os.environ


def test_metrics_collector_counters_and_timings() -> None:
    """Verify thread-safe metric counter accumulation and timing percentiles."""
    collector = MetricsCollector()
    collector.reset()

    collector.increment("http_requests_total", 5)
    collector.increment("cache_hits_total", 2)
    collector.record_timing("llm_latency_ms", 100.0)
    collector.record_timing("llm_latency_ms", 200.0)
    collector.record_timing("llm_latency_ms", 300.0)

    snapshot = collector.get_snapshot()
    assert snapshot["counters"]["http_requests_total"] == 5
    assert snapshot["counters"]["cache_hits_total"] == 2
    assert snapshot["counters"]["cache_misses_total"] == 0

    llm_summary = snapshot["summary"]["llm_latency_ms"]
    assert llm_summary["count"] == 3
    assert llm_summary["avg_ms"] == 200.0
    assert llm_summary["min_ms"] == 100.0
    assert llm_summary["max_ms"] == 300.0
    assert llm_summary["p95_ms"] == 300.0


def test_metrics_collector_reset() -> None:
    """Verify reset wipes all counters and rolling timings."""
    collector = MetricsCollector()
    collector.increment("http_requests_total", 10)
    collector.record_timing("http_duration_ms", 50.0)

    collector.reset()
    snapshot = collector.get_snapshot()
    assert snapshot["counters"]["http_requests_total"] == 0
    assert snapshot["summary"]["http_duration_ms"]["count"] == 0


def test_build_langgraph_trace_config() -> None:
    """Verify LangGraph trace configuration builder produces expected metadata and tags."""
    config = build_langgraph_trace_config(
        correlation_id="corr-12345",
        conversation_id="conv-67890",
        provider="openai",
        model="gpt-4o-mini",
        app_env="production",
    )

    assert config["run_name"] == "langgraph_chatbot_turn"
    assert config["metadata"]["correlation_id"] == "corr-12345"
    assert config["metadata"]["conversation_id"] == "conv-67890"
    assert config["metadata"]["provider"] == "openai"
    assert config["metadata"]["model"] == "gpt-4o-mini"
    assert config["metadata"]["environment"] == "production"
    assert "chatbot" in config["tags"]
    assert "provider:openai" in config["tags"]
    assert "env:production" in config["tags"]


def test_structured_event_logging_functions() -> None:
    """Verify structured event recording functions operate safely and update process metrics."""
    metrics.reset()

    # Cache events
    record_cache_event("cache_hit", "conv-1", "hash-abc", duration_ms=1.5)
    record_cache_event("cache_miss", "conv-1", "hash-xyz", duration_ms=2.0)
    record_cache_event("cache_error", "conv-1", error=Exception("Redis timeout"))

    # Persistence events
    record_persistence_event("history_loaded", "conv-1", message_count=4, duration_ms=10.0)
    record_persistence_event("turn_persisted", "conv-1", message_count=2, duration_ms=15.0)
    record_persistence_event("db_error", "conv-1", error=Exception("DB connection error"))

    # LLM events
    record_llm_event(
        event="llm_generate",
        provider="openai",
        model="gpt-4o-mini",
        duration_ms=250.0,
        input_tokens=15,
        output_tokens=30,
        total_tokens=45,
    )
    record_llm_event(
        event="llm_error",
        provider="openai",
        model="gpt-4o-mini",
        duration_ms=50.0,
        error=Exception("API timeout"),
    )

    snapshot = metrics.get_snapshot()
    assert snapshot["counters"]["cache_hits_total"] == 1
    assert snapshot["counters"]["cache_misses_total"] == 1
    assert snapshot["counters"]["cache_errors_total"] == 1
    assert snapshot["counters"]["persistence_operations_total"] == 3
    assert snapshot["counters"]["persistence_errors_total"] == 1
    assert snapshot["counters"]["llm_requests_total"] == 2
    assert snapshot["counters"]["llm_errors_total"] == 1


@pytest.mark.asyncio
async def test_chat_service_observability_integration(
    test_repository: SQLAlchemyConversationRepository,
) -> None:
    """Verify ChatService records metrics and persistence events during a full turn."""
    metrics.reset()
    mock_llm = MockLLMService(default_response="Observability test response")
    cache = InMemoryCache()
    chat_service = ChatService(
        llm_service=mock_llm,
        conversation_repository=test_repository,
        cache=cache,
        cache_enabled=True,
        cache_ttl_seconds=300,
    )


    response, conv_id = await chat_service.process_message(
        message="Hello observability",
        correlation_id="test-corr-id-001",
    )
    assert response.text == "Observability test response"

    snapshot = metrics.get_snapshot()
    assert snapshot["counters"]["persistence_operations_total"] >= 1
    assert snapshot["counters"]["llm_requests_total"] >= 1
    assert snapshot["counters"]["cache_misses_total"] >= 1

    from app.cache.keys import build_chat_cache_key
    from app.cache.serialization import serialize_cached_response

    # Verify cache hit by creating conv_id2 with cached entry
    conv_id2 = await test_repository.create_conversation()
    user_msg2 = CanonicalMessage.from_text("Cached query", role=MessageRole.USER)
    assistant_msg2 = CanonicalMessage.from_text("Cached response reply", role=MessageRole.ASSISTANT)
    cache_key2 = build_chat_cache_key(
        conversation_id=conv_id2,
        history=[],
        current_user_message=user_msg2,
        provider="mock",
        model="mock-model",
    )
    await cache.set(cache_key2, serialize_cached_response(assistant_msg2), ttl=300)

    cached_response, res_conv_id = await chat_service.process_message(
        message="Cached query",
        conversation_id=conv_id2,
        correlation_id="test-corr-id-002",
    )
    assert cached_response.text == "Cached response reply"
    assert res_conv_id == conv_id2

    snapshot2 = metrics.get_snapshot()
    assert snapshot2["counters"]["cache_hits_total"] >= 1



@pytest.mark.asyncio
async def test_openai_service_usage_and_timing_instrumentation(monkeypatch) -> None:
    """Verify OpenAILLMService records timing and token usage from completion response."""
    metrics.reset()

    fake_response = MagicMock()
    fake_response.id = "chatcmpl-test-obs-123"
    fake_choice = MagicMock()
    fake_choice.message.content = "Instrumented response from OpenAI"
    fake_response.choices = [fake_choice]
    fake_response.usage.prompt_tokens = 12
    fake_response.usage.completion_tokens = 24
    fake_response.usage.total_tokens = 36

    async def mock_create(*args, **kwargs):
        return fake_response

    service = OpenAILLMService(api_key="test-key-mock", model="gpt-4o-mini")
    monkeypatch.setattr(service._client.chat.completions, "create", mock_create)

    messages = [CanonicalMessage.from_text("Test query", role=MessageRole.USER)]
    result = await service.generate(messages)

    assert result.text == "Instrumented response from OpenAI"
    snapshot = metrics.get_snapshot()
    assert snapshot["counters"]["llm_requests_total"] == 1
    assert snapshot["summary"]["llm_latency_ms"]["count"] == 1
