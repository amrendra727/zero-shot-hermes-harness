"""Workspace + dataset routes for the analyst agent."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from src.api._common import api_error, ok
from src.db.models import Dataset, RunRow, Workspace
from src.db.session import get_session
from src.domain import AnalystRunResult
from src.graph.runner import run_agent

router = APIRouter()


def _to_run_result(run: RunRow) -> AnalystRunResult:
    return AnalystRunResult(
        run_id=run.id,
        status=run.status or "completed",
        answer=run.output_text,
        output_text=run.output_text,
        provider=run.provider,
        model=run.model,
        error_message=run.error_message,
    )


@router.post("/workspaces")
def create_workspace(payload: dict, session: Session = Depends(get_session)) -> dict:
    name = str(payload.get("name") or "Untitled workspace").strip()
    workspace = Workspace(name=name, description=payload.get("description"))
    session.add(workspace)
    session.flush()
    return ok({"id": workspace.id, "name": workspace.name, "created_at": workspace.created_at.isoformat() if workspace.created_at else None})


@router.post("/workspaces/{workspace_id}/datasets")
def upload_dataset(workspace_id: str, file: UploadFile, title: str | None = None, session: Session = Depends(get_session)) -> dict:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        raise api_error("workspace_not_found", f"no workspace {workspace_id}", 404)
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise api_error("bad_file_type", "Only .csv uploads are supported in Phase 1.", 415)

    upload_dir = Path("data") / "uploads" / workspace_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / Path(file.filename).name
    try:
        contents = file.file.read()
        dest.write_bytes(contents)
    except Exception as exc:
        raise api_error("upload_failed", str(exc), 500) from exc
    finally:
        file.file.close()

    dataset = Dataset(
        workspace_id=workspace_id,
        name=title or file.filename or "dataset",
        source_filename=file.filename or "dataset.csv",
        storage_path=str(dest),
        row_count=None,
        column_count=None,
        checksum=None,
    )
    session.add(dataset)
    session.flush()

    return ok({
        "dataset_id": dataset.id,
        "filename": dataset.source_filename,
        "columns": [],
        "row_count": dataset.row_count,
        "status": "ready",
    })


@router.post("/workspaces/{workspace_id}/ask")
def ask_workspace(workspace_id: str, payload: dict, session: Session = Depends(get_session)) -> dict:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        raise api_error("workspace_not_found", f"no workspace {workspace_id}", 404)
    question = str(payload.get("question") or "").strip()
    if not question:
        raise api_error("bad_request", "question is required", 400)

    run = run_agent(
        workspace_id=workspace_id,
        question=question,
        insights_toggle=bool(payload.get("insights_toggle")),
    )
    row = session.get(RunRow, run)
    if row is None:
        raise api_error("run_not_found", f"run {run} vanished", 500)
    return ok(_to_run_result(row).model_dump())


@router.get("/workspaces/{workspace_id}/runs")
def list_workspace_runs(workspace_id: str, session: Session = Depends(get_session)) -> dict:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        raise api_error("workspace_not_found", f"no workspace {workspace_id}", 404)
    rows = (
        session.query(RunRow)
        .filter(RunRow.input_text != "__baseline__")
        .order_by(RunRow.created_at.desc())
        .all()
    )
    return ok({
        "workspace_id": workspace_id,
        "runs": [
            {
                "run_id": row.id,
                "question": row.input_text,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "status": row.status,
            }
            for row in rows
        ],
    })
