#!/usr/bin/env python3
"""Batch job runner for scheduled analyst queries.

Reads a JSON/JSONL manifest from --manifest and runs each entry through the agent,
writing results to --out as JSONL.

Usage:
    uv run python scripts/batch_job.py --manifest jobs.jsonl --out results.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _load_entries(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch job runner for analyst queries")
    parser.add_argument("--manifest", required=True, help="Path to JSONL manifest")
    parser.add_argument("--out", required=True, help="Path to write JSONL results")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))

    entries = _load_entries(Path(args.manifest))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    failures = 0

    with out.open("w", encoding="utf-8") as handle:
        for entry in entries:
            try:
                workspace_id = str(entry.get("workspace_id") or "").strip()
                question = str(entry.get("question") or "").strip()
                source_type = str(entry.get("source_type") or "csv").strip()
                if not workspace_id or not question:
                    failures += 1
                    handle.write(json.dumps({"entry": entry, "status": "failed", "error": "missing workspace_id or question"}) + "\n")
                    continue
                from src.graph.runner import run_agent  # noqa: E402
                from src.db.session import create_db_session  # noqa: E402
                from src.db.models import RunRow  # noqa: E402

                run_id = run_agent(
                    workspace_id=workspace_id,
                    question=question,
                    source_type=source_type,
                    insights_toggle=bool(entry.get("insights_toggle")),
                )
                with create_db_session() as session:
                    row = session.get(RunRow, run_id)
                    if row is None:
                        failures += 1
                        handle.write(json.dumps({"entry": entry, "status": "failed", "error": "run vanished"}) + "\n")
                        continue
                    payload = {
                        "entry": entry,
                        "status": row.status or "completed",
                        "run_id": row.id,
                        "answer": row.output_text,
                        "provider": row.provider,
                        "model": row.model,
                        "error": row.error_message,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                    }
            except Exception as exc:  # noqa: BLE001
                failures += 1
                payload = {"entry": entry, "status": "failed", "error": str(exc)}
            handle.write(json.dumps(payload) + "\n")

    print(f"Batch complete: wrote {out} (failures={failures})")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
