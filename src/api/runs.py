"""Runs API — baseline /runs + analyst workspace surface."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api._common import api_error, ok
from src.db.models import RunRow
from src.db.session import get_session
from src.domain import AnalystRunRequest, AnalystRunResult, RunRequest, RunResult
from src.graph.runner import run_agent

router = APIRouter()


def _to_result(run: RunRow) -> RunResult:
    return RunResult(
        run_id=run.id,
        status=run.status,
        output_text=run.output_text,
        provider=run.provider,
        model=run.model,
        error_message=run.error_message,
    )


@router.post("/runs")
def create_run(req: RunRequest, session: Session = Depends(get_session)) -> dict:
    # Baseline bridge: reuse the analyst runner for backward compatibility.
    run = run_agent("__baseline__", req.text)
    row = session.get(RunRow, run)
    if row is None:  # pragma: no cover — write happened in run_agent
        raise api_error("run_not_found", f"run {run} vanished", 500)
    if row.status == "failed":
        return ok(_to_result(row).model_dump())
    return ok(_to_result(row).model_dump())


@router.get("/runs/{run_id}")
def get_run(run_id: str, session: Session = Depends(get_session)) -> dict:
    run = session.get(RunRow, run_id)
    if run is None:
        raise api_error("run_not_found", f"no run with id {run_id}", 404)
    return ok(_to_result(run).model_dump())
