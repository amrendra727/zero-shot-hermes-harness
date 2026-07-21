"""Graph assembly — StateGraph compiled once at import."""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.graph.edges import is_error
from src.graph.nodes import (
    error_handler,
    execute_query,
    finalize,
    format_outputs,
    generate_query,
    intake_plan,
    select_source,
    surface_toggle,
    transform_text,
)
from src.graph.state import AnalystState


def _route_after(state: AnalystState, on_success: str) -> str:
    return "error_handler" if is_error(state) == "error_handler" else on_success


def _build_graph():
    g = StateGraph(AnalystState)

    g.add_node("transform_text", transform_text)
    g.add_node("intake_plan", intake_plan)
    g.add_node("select_source", select_source)
    g.add_node("generate_query", generate_query)
    g.add_node("execute_query", execute_query)
    g.add_node("format_outputs", format_outputs)
    g.add_node("surface_toggle", surface_toggle)
    g.add_node("error_handler", error_handler)
    g.add_node("finalize", finalize)

    g.set_entry_point("intake_plan")
    g.add_conditional_edges(
        "intake_plan",
        lambda state: _route_after(state, "select_source"),
        {"select_source": "select_source", "error_handler": "error_handler"},
    )
    g.add_conditional_edges(
        "select_source",
        lambda state: _route_after(state, "generate_query"),
        {"generate_query": "generate_query", "error_handler": "error_handler"},
    )
    g.add_conditional_edges(
        "generate_query",
        lambda state: _route_after(state, "execute_query"),
        {"execute_query": "execute_query", "error_handler": "error_handler"},
    )
    g.add_conditional_edges(
        "execute_query",
        lambda state: _route_after(state, "format_outputs"),
        {"format_outputs": "format_outputs", "error_handler": "error_handler"},
    )
    g.add_conditional_edges(
        "format_outputs",
        lambda state: _route_after(state, "surface_toggle"),
        {"surface_toggle": "surface_toggle", "error_handler": "error_handler"},
    )
    g.add_conditional_edges(
        "surface_toggle",
        lambda state: _route_after(state, "finalize"),
        {"finalize": "finalize", "error_handler": "error_handler"},
    )

    g.add_edge("error_handler", "finalize")
    g.add_edge("finalize", END)
    return g.compile()


agentic_ai = _build_graph()
