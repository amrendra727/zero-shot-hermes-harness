"""Edges for the analyst graph."""
from __future__ import annotations

from src.graph.state import AnalystState


def is_error(state: AnalystState) -> str:
    if state.get("error"):
        return "handle_error"
    return "finalize"


def after_transform(state: AnalystState) -> str:
    return is_error(state)
