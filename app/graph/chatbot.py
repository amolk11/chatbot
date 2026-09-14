"""LangGraph chatbot workflow builder and compilation."""

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graph.nodes import GenerateNode, format_node, validate_node
from app.graph.state import ChatGraphState
from app.llm.interfaces import ILLMService


def build_chat_graph(llm_service: ILLMService) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Construct and compile the standard chatbot workflow graph with injected LLM service."""
    builder = StateGraph(ChatGraphState)

    # Register workflow nodes
    builder.add_node("validate", validate_node)
    builder.add_node("generate", GenerateNode(llm_service))
    builder.add_node("format", format_node)

    # Define execution edges: START -> validate -> generate -> format -> END
    builder.add_edge(START, "validate")
    builder.add_edge("validate", "generate")
    builder.add_edge("generate", "format")
    builder.add_edge("format", END)

    return builder.compile()
