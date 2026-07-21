
# Architecture — UP Police Data Analyst Agent

## System Overview

The agent is a FastAPI service that exposes a web UI, REST API, CLI,
and batch runner around one runtime: a LangGraph agent whose job is to
turn a natural-language question over a configured data source into an
answer with supporting evidence.

In Phase 1 the data source is user-uploaded CSV(s). In Phase 2 a live
MsSQL source is added with cached summaries to keep DB load low.

## Components

- **API layer** — FastAPI routes under `src/api/`. Serves the static
  frontend at `/app`, health at `/health`, and workspace/runs routes
  at `/api/v1/...`.
- **Workspace store** — `src/db/` using SQLAlchemy on SQLite for the
  app metadata: runs, workspaces, uploaded files, cached questions,
  artifacts. Does not store production police data in Phase 1 unless
  necessary; prefer ephemeral columnar processing for CSV payloads.
- **Data ingestion** — CSV parsing + schema inference using Python
  stdlib / pandas-light path. Streaming ingestion for large files.
- **Agent runtime** — LangGraph state machine in `src/graph/` with
  nodes: intake/plan, tool selection, execute query, format outputs,
  surface SQL, optional follow-up suggestions.
- **LLM provider layer** — OpenAI-compatible client wired to NVIDIA
  NIM in `.env`. Used for NL planning, SQL generation, summarization,
  anomaly flagging, and chart suggestion text.
- **Observability** — `src/observability/` structured log of request
  summary, latency, error class, workspace id, source type.

## Data Flow

```
User
  │
  ▼
Frontend / REST / CLI / Batch runner
  │
  ▼
API layer
  │
  ▼
Agent runtime
  │   ├─ CSV workspace
  │   │    ├─ Parse uploaded CSV(s)
  │   │    ├─ Profile schema + sample values
  │   │    └─ Load into in-memory / temp dataset view
  │   │
  │   └─ MsSQL workspace  ← Phase 2
  │       ├─ Read summary cache
  │       └─ Issue parameterized queries through Db session
  ▼
LLM provider via NIM
  │
  ▼
Formatted response → UI / API / artifact download
```

## Deployment / runtime

- Local-first.
- Network boundary enforced by deployment: bind to `127.0.0.1`, no
  outbound exfil routes configured.
- `.env` never committed; secrets stay on host.

## Stack

- **Language:** Python 3.11+
- **API:** FastAPI + uvicorn
- **Agent framework:** LangGraph
- **DB / workspace metadata:** SQLAlchemy + SQLite
- **LLM provider:** NVIDIA NIM, OpenAI-compatible HTTP client
- **Frontend:** zero-build static app in `frontend/public/`
- **Package manager:** uv
- **Migrations:** Alembic
- **Observability:** structlog
- **Tests:** pytest
