"""AgentState — the TypedDict flowing through the graph."""
from __future__ import annotations

from typing import Any, TypedDict


class AnalystState(TypedDict, total=False):
    run_id: str
    workspace_id: str
    source_type: str
    question: str
    insights_toggle: bool
    plan: list[str]
    sql_or_transform: str
    result_rows: list[dict[str, Any]]
    answer: str
    output_text: str
    follow_ups: list[str]
    anomalies: list[str]
    sql_suggestion: str
    chart_spec: dict[str, Any] | None
    report_artifact_path: str | None
    events: list[dict[str, Any]]
    provider: str | None
    model: str | None
    status: str | None
    error: str | None
