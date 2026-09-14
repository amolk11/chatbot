"""LangGraph and LangChain distributed tracing configuration helpers."""

from typing import Any


def build_langgraph_trace_config(
    correlation_id: str | None = None,
    conversation_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    app_env: str | None = None,
) -> dict[str, Any]:
    """Build a RunnableConfig dictionary for LangGraph / LangChain execution tracing.

    Extracts execution context and sets run names, metadata, and tags for LangSmith
    distributed tracing while remaining fully functional when tracing is disabled.

    Args:
        correlation_id: Correlation / request tracking identifier.
        conversation_id: Persistent conversation identifier.
        provider: Active LLM provider name (e.g. 'openai', 'mock').
        model: Active model identifier.
        app_env: Deployment environment name (e.g. 'development', 'production').

    Returns:
        A dictionary conformant to LangChain RunnableConfig schema.
    """
    metadata: dict[str, Any] = {}
    tags: list[str] = ["chatbot"]

    if correlation_id:
        metadata["correlation_id"] = correlation_id
    if conversation_id:
        metadata["conversation_id"] = conversation_id
    if provider:
        metadata["provider"] = provider
        tags.append(f"provider:{provider}")
    if model:
        metadata["model"] = model
    if app_env:
        metadata["environment"] = app_env
        tags.append(f"env:{app_env}")

    config: dict[str, Any] = {
        "run_name": "langgraph_chatbot_turn",
        "metadata": metadata,
        "tags": tags,
    }

    return config
