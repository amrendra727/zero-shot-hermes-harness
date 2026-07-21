
# Data — UP Police Data Analyst Agent

## Workspace Metadata

| Entity | Purpose | Storage |
| --- | --- | --- |
| workspace | User-created investigation workspace | SQLite via SQLAlchemy |
| dataset | Uploaded CSV metadata for a workspace | SQLite via SQLAlchemy |
| run | One question/answer trace | SQLite via SQLAlchemy |
| artifact | Chart/report file references | SQLite + filesystem under `artifacts/` |

## CSV Data Contract

- Each uploaded CSV becomes a `dataset` with inferred column names,
  types, and sample values.
- The agent never mutates the uploaded file; transformations are read
  operations or derived views.
- Large CSV support uses chunked parsing into queryable in-memory
  structures; phase 1 keeps it simple and bounded.

## MsSQL Data Contract (Phase 2)

- Read-only account with parameterized queries only.
- Preferred access path: cached summary tables refreshed on schedule
  by DBA, not by the agent runtime.
- Connection details supplied via `.env` template; never committed.

## Retention

- Workspace metadata retained until user deletes workspace.
- Artifact files retained until cleanup job removes old runs.
