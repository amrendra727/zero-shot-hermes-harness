"""Domain models for analyst-visible run results."""
from __future__ import annotations

from pydantic import BaseModel, Field


class AnalystRunRequest(BaseModel):
    workspace_id: str = Field(...)
    question: str = Field(..., min_length=1, max_length=1000)
    insights_toggle: bool = Field(default=False)


class AnalystRunResult(BaseModel):
    run_id: str
    status: str
    answer: str | None = None
    output_text: str | None = None
    table: dict | None = None
    chart_spec: dict | None = None
    sql_suggestion: str | None = None
    follow_ups: list[str] = []
    anomalies: list[str] = []
    provider: str | None = None
    model: str | None = None
    error_message: str | None = None
