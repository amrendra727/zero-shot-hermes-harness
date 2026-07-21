
# Agent Graph — UP Police Data Analyst

## Pattern

Plan-and-execute conversational analyst with optional follow-up suggestions.
Cite `harness/patterns/agentic-ai.md`: **planner-executor with tool-use**
and **memory-backed persistence**.

## State

```python
class AnalystState(TypedDict):
    workspace_id: str
    source_type: str  # "csv" | "mssql"
    question: str
    insights_toggle: bool
    plan: list[str]
    sql_or_transform: str
    result_rows: list[dict]
    answer: str
    follow_ups: list[str]
    anomalies: list[str]
    sql_suggestion: str
    chart_spec: dict | None
    report_artifact_path: str | None
    events: list[dict]
```

## Nodes

- **intake_plan**
  - Inputs: `question`, `insights_toggle`, workspace schema summary.
  - Outputs: `plan[]` listing required retrieval steps.
  - Failure: fallback to single-step retrieval; record `events[]`.

- **select_source**
  - Choose CSV workspace or MsSQL workspace based on `workspace_id`.
  - Load schema summary and access config from workspace store.

- **generate_query**
  - Inputs: `plan[]`, schema summary.
  - Outputs: `sql_or_transform`, optional `chart_spec`.
  - External calls: NVIDIA NIM completion.
  - On failure: ask for clarification in conversational fallback mode.

- **execute_query**
  - For CSV: apply query/logic against in-memory dataset.
  - For MsSQL: run parameterized query with read-only account.
  - Outputs: `result_rows`.

- **format_outputs**
  - Build NL answer, table data, ranked lists, anomalies, follow-ups,
    `sql_suggestion`, optional chart spec, optional report artifact path.

- **surface_toggle**
  - If `insights_toggle` is True: attach `follow_ups`, `anomalies`,
    hotspot calls.
  - If False: emit only requested summary + evidence.

- **error_handler**
  - Classify failures: schema ambiguity, unsafe SQL, provider error,
    empty result, DB access failure.
  - Produce user-facing remediation.

- **finalize**
  - Persist run, update workspace history, return rendered response.

## Edges

- `START` -> `intake_plan`
- `intake_plan` -> `select_source`
- `select_source` -> `generate_query`
- `generate_query` -> `execute_query`
- `execute_query` -> `format_outputs`
- `format_outputs` -> `surface_toggle`
- `surface_toggle` -> `finalize`
- `finalize` -> `END`
- Any node -> `error_handler` -> `finalize`

## Concurrency

Phase 1: sequential per question; Phase 2 may parallelize unrelated
batch jobs with separate workflow instances.

## Assembly pseudocode

```python
workflow = StateGraph(AnalystState)
workflow.add_node("intake_plan", intake_plan_node)
workflow.add_node("select_source", select_source_node)
workflow.add_node("generate_query", generate_query_node)
workflow.add_node("execute_query", execute_query_node)
workflow.add_node("format_outputs", format_outputs_node)
workflow.add_node("surface_toggle", surface_toggle_node)
workflow.add_node("error_handler", error_handler_node)
workflow.add_node("finalize", finalize_node)

workflow.add_edge(START, "intake_plan")
workflow.add_edge("intake_plan", "select_source")
workflow.add_edge("select_source", "generate_query")
workflow.add_edge("generate_query", "execute_query")
workflow.add_edge("execute_query", "format_outputs")
workflow.add_edge("format_outputs", "surface_toggle")
workflow.add_edge("surface_toggle", "finalize")
workflow.add_edge("finalize", END)

for node in ALL_NODES:
    workflow.add_edge(node, "error_handler", condition=is_error)

app = workflow.compile()
```
