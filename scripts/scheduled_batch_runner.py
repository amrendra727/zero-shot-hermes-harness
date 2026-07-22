#!/usr/bin/env python3
"""Scheduled batch runner for analyst agent jobs.

Usage:
    # Process all queued jobs once
    uv run python scripts/scheduled_batch_runner.py --run-once

    # Watch the queue directory and process jobs as they arrive
    uv run python scripts/scheduled_batch_runner.py --watch

    # Process jobs with a custom interval (seconds)
    uv run python scripts/scheduled_batch_runner.py --watch --interval 30
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
_QUEUE_DIR = ROOT / "data" / "upload-queue"
_OUT_DIR = ROOT / "data" / "batch-results"


def _load_queued_jobs() -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    if not _QUEUE_DIR.exists():
        return jobs
    for path in sorted(_QUEUE_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("status") == "queued":
                jobs.append(payload)
        except Exception:
            continue
    return jobs


def _mark_job(payload: dict[str, Any], status: str, error: str | None = None) -> None:
    payload["status"] = status
    payload["attempts"] = int(payload.get("attempts") or 0) + 1
    if error:
        payload["last_error"] = error
    path = _QUEUE_DIR / f"{payload['job_id']}.json"
    if path.exists():
        path.write_text(json.dumps(payload), encoding="utf-8")


def _write_result(payload: dict[str, Any], result: dict[str, Any]) -> Path:
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _OUT_DIR / f"{payload['job_id']}.json"
    out_path.write_text(json.dumps({"job": payload, "result": result}, indent=2), encoding="utf-8")
    return out_path


def _process_job(job: dict[str, Any]) -> dict[str, Any]:
    from src.db.session import create_db_session  # noqa: E402
    from src.db.models import RunRow  # noqa: E402
    from src.graph.runner import run_agent  # noqa: E402

    workspace_id = str(job.get("workspace_id") or "").strip()
    question = f"Analyze dataset: {job.get('filename', '')}"
    source_type = str(job.get("source_type") or "csv").strip()
    insights_toggle = bool(job.get("insights_toggle"))

    if not workspace_id:
        raise ValueError("missing workspace_id")

    run_id = run_agent(
        workspace_id=workspace_id,
        question=question,
        source_type=source_type,
        insights_toggle=insights_toggle,
    )
    with create_db_session() as session:
        row = session.get(RunRow, run_id)
        if row is None:
            raise RuntimeError("run vanished after execution")
        return {
            "run_id": row.id,
            "status": row.status or "completed",
            "answer": row.output_text,
            "provider": row.provider,
            "model": row.model,
            "error": row.error_message,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }


def run_once() -> int:
    jobs = _load_queued_jobs()
    failures = 0
    for job in jobs:
        try:
            result = _process_job(job)
            _write_result(job, result)
            _mark_job(job, "completed")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            _mark_job(job, "failed", str(exc))
    print(f"Scheduled run complete: processed {len(jobs)} job(s), failures={failures}")
    return 1 if failures else 0


def watch(interval: int = 30) -> int:
    print(f"Watching {_QUEUE_DIR} for queued jobs (interval={interval}s). Ctrl+C to stop.")
    try:
        while True:
            run_once()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Scheduled batch runner for analyst agent jobs")
    parser.add_argument("--run-once", action="store_true", help="Process queued jobs once and exit")
    parser.add_argument("--watch", action="store_true", help="Watch queue and process jobs on an interval")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds for --watch")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))
    os.environ.setdefault("PYTHONPATH", str(ROOT))

    if args.watch:
        return watch(interval=args.interval)
    return run_once()


if __name__ == "__main__":
    raise SystemExit(main())
