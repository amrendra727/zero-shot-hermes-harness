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


@router.post("/workspaces")
def create_workspace(req: AnalystRunRequest, session: Session = Depends(get_session)) -> dict:
    return ok({"status": "deferred", "message": "Use the /runs path in Phase 1."})


@router.get("/workspaces/{workspace_id}/runs")
def list_workspace_runs(workspace_id: str, session: Session = Depends(get_session)) -> dict:
    return ok({"status": "deferred", "message": "Use GET /runs/{run_id} in Phase 1."})


@router.post("/workspaces/{workspace_id}/ask")
def ask_workspace(req: AnalystRunRequest, session: Session = Depends(get_session)) -> dict:
    run_id = run_agent(req.workspace_id, req.question, req.insights_toggle)
    row = session.get(RunRow, run_id)
    if row is None:  # pragma: no cover — write happened in run_agent
        raise api_error("run_not_found", f"run {run_id} vanished", 500)

    result = AnalystRunResult(
        run_id=row.id,
        status=row.status or "completed",
        answer=row.output_text,
        output_text=row.output_text,
        provider=row.provider,
        model=row.model,
        error_message=row.error_message,
    )
    return ok(result.model_dump())
