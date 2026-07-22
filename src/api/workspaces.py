"""Workspace + dataset routes for the analyst agent."""
from __future__ import annotations

import json
import os
import uuid
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
_QUEUE_DIR = Path("data") / "upload-queue"
_QUEUE_DIR.mkdir(parents=True, exist_ok=True)


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


def _enqueue(workspace_id: str, dataset_id: str, filename: str) -> dict[str, object]:
    payload = {
        "job_id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "dataset_id": dataset_id,
        "filename": filename,
        "status": "queued",
        "attempts": 0,
    }
    path = _QUEUE_DIR / f"{payload['job_id']}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


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
    job = _enqueue(workspace_id=workspace_id, dataset_id=str(dataset.id), filename=dataset.source_filename)

    return ok({
        "dataset_id": dataset.id,
        "filename": dataset.source_filename,
        "columns": [],
        "row_count": dataset.row_count,
        "status": "queued",
        "job_id": job.get("job_id"),
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


@router.get("/workspaces/{workspace_id}/queue")
def list_workspace_queue(workspace_id: str) -> dict:
    jobs = []
    if _QUEUE_DIR.exists():
        for path in _QUEUE_DIR.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if payload.get("workspace_id") == workspace_id:
                    jobs.append(payload)
            except Exception:
                continue
    jobs.sort(key=lambda item: item.get("job_id", ""), reverse=True)
    return ok({"jobs": jobs, "count": len(jobs)})
