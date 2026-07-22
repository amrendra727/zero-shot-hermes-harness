#!/usr/bin/env python3
"""CLI runner for the UP Police analyst agent.

Usage:
    uv run python scripts/run_analyst_cli.py --workspace <workspace_id> --question "Top 5 incidents"
    uv run python scripts/run_analyst_cli.py --workspace <workspace_id> --question "..." --source mssql
    uv run python scripts/run_analyst_cli.py --help
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="UP Police analyst agent CLI")
    parser.add_argument("--workspace", required=True, help="Workspace ID to query")
    parser.add_argument("--question", required=True, help="Natural-language question")
    parser.add_argument("--source", default="csv", choices=["csv", "mssql"], help="Data source type")
    parser.add_argument("--insights", action="store_true", help="Enable insights/follow-ups")
    parser.add_argument("--json", action="store_true", help="Print raw JSON result")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))
    os.environ.setdefault("PYTHONPATH", str(ROOT))

    from src.graph.runner import run_agent  # noqa: E402
    from src.db.session import create_db_session  # noqa: E402
    from src.db.models import RunRow  # noqa: E402

    run_id = run_agent(
        workspace_id=args.workspace,
        question=args.question,
        source_type=args.source,
        insights_toggle=args.insights,
    )
    with create_db_session() as session:
        row = session.get(RunRow, run_id)
        if row is None:
            print(f"Run {run_id} not found.", file=sys.stderr)
            return 1
        result = {
            "run_id": row.id,
            "status": row.status,
            "answer": row.output_text,
            "provider": row.provider,
            "model": row.model,
            "error": row.error_message,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Run ID: {result['run_id']}")
        print(f"Status: {result['status']}")
        print(f"Answer: {result['answer']}")
        if result["error"]:
            print(f"Error: {result['error']}", file=sys.stderr)
    return 0 if (result.get("status") != "failed") else 2


if __name__ == "__main__":
    raise SystemExit(main())
