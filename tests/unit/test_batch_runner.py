"""Integration-style tests for upload queue + scheduled batch runner path."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYTHONPATH", str(ROOT))


def _write_job(workspace_id: str, filename: str = "sample.csv") -> dict[str, object]:
    payload = {
        "job_id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "dataset_id": str(uuid.uuid4()),
        "filename": filename,
        "status": "queued",
        "attempts": 0,
        "source_type": "csv",
        "question": "Summarize this dataset",
        "insights_toggle": False,
    }
    path = ROOT / "data" / "upload-queue" / f"{payload['job_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def test_queued_job_is_processed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.scheduled_batch_runner import run_once  # noqa: E402

    monkeypatch.setenv("AGENT_LLM_PROVIDER", "stub")
    workspace_id = "ws-queue-test"
    job = _write_job(workspace_id=workspace_id, filename="crimes.csv")

    rc = run_once()
    assert rc == 0

    job_path = ROOT / "data" / "upload-queue" / f"{job['job_id']}.json"
    payload = json.loads(job_path.read_text(encoding="utf-8"))
    assert payload["status"] == "completed"
    assert payload["attempts"] == 1

    result_path = ROOT / "data" / "batch-results" / f"{job['job_id']}.json"
    assert result_path.exists()
    result_payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert result_payload["job"]["job_id"] == job["job_id"]
    assert result_payload["result"]["status"] in {"completed", "failed"}


def test_failed_job_is_marked_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.scheduled_batch_runner import run_once  # noqa: E402

    workspace_id = "ws-bad"
    job = _write_job(workspace_id=workspace_id, filename="bad.csv")
    job_path = ROOT / "data" / "upload-queue" / f"{job['job_id']}.json"
    job_path.write_text(json.dumps({**job, "workspace_id": ""}), encoding="utf-8")

    rc = run_once()
    assert rc == 1

    payload = json.loads(job_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["attempts"] == 1
    assert "missing" in json.dumps(payload)
