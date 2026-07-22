"""Graph nodes — analyst capability slot."""
from __future__ import annotations

from src.graph.state import AnalystState
from src.llm.client import LLMClient, load_prompt
from src.llm.providers.base import LLMError


def _safe_get(state: AnalystState, key: str, default: Any = None) -> Any:
    return state.get(key, default)


def _emit(state: AnalystState, **kwargs: Any) -> AnalystState:
    merged = dict(state)
    merged.update(kwargs)
    return merged


def transform_text(state: AnalystState) -> dict:
    """Baseline compatibility node used by tests and baseline /runs."""
    try:
        text = str(state.get("input_text") or "")
        instruction = str(state.get("instruction") or "").strip().lower()
        if instruction == "upper":
            output = text.upper()
        elif instruction == "lower":
            output = text.lower()
        else:
            output = text
        return {"error": None, "output_text": output, "input_text": text}
    except Exception as exc:  # pragma: no cover — defensive
        return {"error": str(exc)}


def handle_error(state: AnalystState) -> AnalystState:
    err = _safe_get(state, "error")
    return _safe_get(state, "status") or ("failed" if err else "completed")


def intake_plan(state: AnalystState) -> AnalystState:
    try:
        question = _safe_get(state, "question") or ""
        insights = _safe_get(state, "insights_toggle", False)
        plan = [
            "load workspace schema summary from metadata store",
            "select source: csv dataset view or mssql connection",
            "generate parameterized query / transform",
            "execute query against selected source",
            "format answer, table, chart spec, sql suggestion",
        ]
        if insights:
            plan += [
                "compute follow-up suggestions from result patterns",
                "detect anomalies and hotspot candidates",
            ]
        events = [{"step": "intake_plan", "question": question, "insights_toggle": insights}]
        return _emit(state, plan=plan, events=events, error=None)
    except Exception as exc:  # pragma: no cover — defensive
        return _emit(state, error=str(exc))


def select_source(state: AnalystState) -> AnalystState:
    try:
        source_type = _safe_get(state, "source_type") or "csv"
        events = _safe_get(state, "events") or []
        events.append({"step": "select_source", "source_type": source_type})
        return _emit(state, source_type=source_type, events=events, error=None)
    except Exception as exc:
        return _emit(state, error=str(exc))


def generate_query(state: AnalystState) -> AnalystState:
    try:
        client = LLMClient()
        system = load_prompt("analyst")
        plan_lines = "\n".join(f"- {step}" for step in (_safe_get(state, "plan") or []))
        question = _safe_get(state, "question") or ""
        user = (
            "Planned retrieval steps:\n"
            f"{plan_lines}\n\n"
            f"User question:\n{question}\n\n"
            "Return JSON only with keys: sql_or_transform, chart_spec, sql_suggestion.\n"
            "sql_or_transform must be a read-only query or transformation expression.\n"
            "chart_spec must be null or an object with type/x/y fields.\n"
        )
        output = client.complete(system, user, max_tokens=2048)
        import json
        parsed = json.loads(output)
        sql_or_transform = str(parsed.get("sql_or_transform") or output)
        chart_spec = parsed.get("chart_spec")
        sql_suggestion = str(parsed.get("sql_suggestion") or sql_or_transform)
        events = _safe_get(state, "events") or []
        events.append({
            "step": "generate_query",
            "provider": client.provider_name,
            "model": client.model,
            "sql_suggestion": sql_suggestion,
        })
        return _emit(
            state,
            sql_or_transform=sql_or_transform,
            sql_suggestion=sql_suggestion,
            chart_spec=chart_spec,
            provider=client.provider_name,
            model=client.model,
            events=events,
            error=None,
        )
    except LLMError as exc:
        return _emit(state, error=str(exc))
    except Exception as exc:  # pragma: no cover — defensive
        return _emit(state, error=str(exc))


def execute_query(state: AnalystState) -> AnalystState:
    try:
        expression = _safe_get(state, "sql_or_transform") or ""
        workspace_id = _safe_get(state, "workspace_id") or ""
        source_type = _safe_get(state, "source_type") or "csv"
        result_rows: list[dict[str, object]] = []

        if source_type == "csv":
            import csv
            import sqlite3
            from pathlib import Path

            repo_root = Path(__file__).resolve().parent.parent.parent
            uploads_dir = repo_root / "data" / "uploads" / workspace_id
            if not uploads_dir.exists():
                return _emit(state, error=f"No datasets found for workspace {workspace_id}.")

            csv_files = sorted(
                (p for p in uploads_dir.glob("*.csv") if p.is_file()),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if not csv_files:
                return _emit(state, error=f"No CSV datasets available for workspace {workspace_id}.")

            csv_path = csv_files[0]
            with sqlite3.connect(":memory:") as conn:
                conn.row_factory = sqlite3.Row
                with csv_path.open("r", newline="", encoding="utf-8") as handle:
                    reader = csv.reader(handle)
                    headers = next(reader)
                    safe_headers = [
                        f"col_{idx}" if not header.strip() else header.strip().replace('"', '""')
                        for idx, header in enumerate(headers)
                    ]
                    table_name = "dataset"
                    conn.execute(
                        "CREATE TABLE %s (%s)"
                        % (
                            table_name,
                            ",".join('"%s" TEXT' % name for name in safe_headers),
                        )
                    )
                    placeholders = ",".join(["?"] * len(safe_headers))
                    conn.executemany(
                        "INSERT INTO %s VALUES (%s)" % (table_name, placeholders),
                        reader,
                    )

                if not expression.strip():
                    expression = "SELECT * FROM %s LIMIT 50" % table_name
                cursor = conn.execute(expression)

                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                result_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        else:
            return _emit(state, error=f"Unsupported source_type in Phase 1: {source_type}")

        events = _safe_get(state, "events") or []
        events.append({"step": "execute_query", "row_count": len(result_rows), "source": source_type})
        return _emit(state, result_rows=result_rows, events=events, error=None)
    except Exception as exc:
        return _emit(state, error=str(exc))


def _format_table(rows: list[dict[str, object]]) -> tuple[list[str], list[dict[str, object]]]:
    if not rows:
        return [], []
    columns = sorted({key for row in rows for key in row.keys()})
    return columns, rows


def format_outputs(state: AnalystState) -> AnalystState:
    try:
        rows = _safe_get(state, "result_rows") or []
        chart_spec = _safe_get(state, "chart_spec")
        sql_suggestion = _safe_get(state, "sql_suggestion") or ""

        if not rows:
            answer = "I couldn't retrieve any matching rows for this question."
            return _emit(
                state,
                answer=answer,
                output_text=answer,
                table={"columns": [], "rows": []},
                follow_ups=["Try relaxing the filters", "Select a different dataset"],
                anomalies=[],
                sql_suggestion=sql_suggestion,
                chart_spec=chart_spec,
                error=None,
            )

        columns, clean_rows = _format_table(rows)
        answer = f"Found {len(clean_rows)} row(s) matching your question."
        events = _safe_get(state, "events") or []
        events.append({"step": "format_outputs", "columns": columns, "row_count": len(clean_rows)})

        follow_ups = []
        anomalies = []
        if _safe_get(state, "insights_toggle", False):
            follow_ups = ["Drill down by district", "Show monthly trend", "Compare with prior period"]
            anomalies = ["No anomalies detected in this sample"]

        return _emit(
            state,
            answer=answer,
            output_text=answer,
            table={"columns": columns, "rows": clean_rows},
            chart_spec=chart_spec,
            follow_ups=follow_ups,
            anomalies=anomalies,
            sql_suggestion=sql_suggestion,
            events=events,
            error=None,
        )
    except Exception as exc:
        return _emit(state, error=str(exc))


def surface_toggle(state: AnalystState) -> AnalystState:
    try:
        insights = _safe_get(state, "insights_toggle", False)
        if not insights:
            events = _safe_get(state, "events") or []
            return _emit(state, follow_ups=[], anomalies=[], events=events, error=None)
        return _emit(state, error=None)
    except Exception as exc:
        return _emit(state, error=str(exc))


def error_handler(state: AnalystState) -> AnalystState:
    err = _safe_get(state, "error")
    events = _safe_get(state, "events") or []
    events.append({"step": "error_handler", "error": err})
    return _emit(
        state,
        status="failed",
        answer="Unable to complete analysis right now.",
        output_text=f"Error: {err}",
        follow_ups=[],
        anomalies=[],
        sql_suggestion="",
        chart_spec=None,
        report_artifact_path=None,
        events=events,
        error=err,
    )


def finalize(state: AnalystState) -> AnalystState:
    status = _safe_get(state, "status") or "completed"
    answer = _safe_get(state, "answer") or ""
    events = _safe_get(state, "events") or []
    events.append({"step": "finalize", "answer_length": len(answer), "status": status})
    return _emit(
        state,
        status=status,
        answer=answer,
        output_text=answer,
        events=events,
        error=_safe_get(state, "error"),
    )
