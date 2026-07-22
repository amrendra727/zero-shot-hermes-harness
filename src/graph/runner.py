"""run_agent() — the entry point the API calls.

Creates the run row, invokes the graph, persists the outcome. Errors land in
the row (status=failed + message), never as a crash.
"""
from __future__ import annotations

from src.db.models import RunRow
from src.db.session import create_db_session
from src.graph.agent import agentic_ai
from src.graph.state import AnalystState
from src.observability.events import get_logger, log_span


def run_agent(workspace_id: str, question: str, insights_toggle: bool = False) -> str:
    log = get_logger("runner")

    with create_db_session() as session:
        run = RunRow(
            input_text=question,
            instruction="analyst-qna",
            status="running",
        )
        session.add(run)
        session.flush()
        run_id = run.id

    initial: AnalystState = {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "source_type": "csv",
        "question": question,
        "insights_toggle": insights_toggle,
        "error": None,
    }
    with log_span(log, "agent_run", run_id=run_id) as span:
        final_state: AnalystState = agentic_ai.invoke(initial)
        span["status"] = final_state.get("status", "completed")

    output_text = final_state.get("answer") or final_state.get("output_text") or ""
    status = final_state.get("status", "completed")
    if status != "failed" and final_state.get("error"):
        status = "failed"
    with create_db_session() as session:
        run = session.get(RunRow, run_id)
        if run is None:
            raise RuntimeError("Run row vanished mid-flight.")
        run.output_text = output_text
        run.provider = final_state.get("provider")
        run.model = final_state.get("model")
        run.status = status
        run.error_message = final_state.get("error") or run.error_message

    return run_id
