
# API — UP Police Data Analyst Agent

## API Style

REST (`/api/v1/...`) plus static UI under `/app`.

## Endpoints / Commands

### `POST /api/v1/workspaces`

**Purpose.** Create a new investigation workspace.

**Request:**
```json
{
  "name": "Zone-3 Weekly Review",
  "source_type": "csv"
}
```

**Response:**
```json
{
  "id": "ws_123",
  "name": "Zone-3 Weekly Review",
  "source_type": "csv",
  "created_at": "2026-07-21T04:00:00Z"
}
```

**Error cases:**
- 400 — invalid name or source_type
- 409 — name already exists for user/context

### `POST /api/v1/workspaces/{workspace_id}/datasets`

**Purpose.** Attach a CSV dataset to a workspace.

**Request:** `multipart/form-data` with `file`.

**Response:**
```json
{
  "dataset_id": "ds_1",
  "filename": "incidents_2026.csv",
  "columns": ["station", "date", "crime_type", "lat", "lon"],
  "row_count": 5421,
  "status": "ready"
}
```

**Error cases:**
- 400 — unsupported file type
- 413 — file too large
- 422 — parse/schema failure

### `POST /api/v1/workspaces/{workspace_id}/ask`

**Purpose.** Ask a natural-language question against a workspace.

**Request:**
```json
{
  "question": "Top 5 stations by total incidents this month.",
  "insights_toggle": true
}
```

**Response:**
```json
{
  "run_id": "run_456",
  "answer": "...",
  "table": { "columns": [...], "rows": [...] },
  "chart_spec": { "type": "bar", "x": "station", "y": "count" },
  "sql_suggestion": "SELECT station, COUNT(*) ...",
  "follow_ups": [...],
  "anomalies": [...],
  "latency_ms": 4820
}
```

**Error cases:**
- 400 — missing question
- 404 — workspace not found
- 422 — question cannot be answered from current data

### `GET /api/v1/workspaces/{workspace_id}/runs`

**Purpose.** List prior questions/answers in a workspace.

**Response:**
```json
{
  "runs": [
    {
      "run_id": "run_456",
      "question": "...",
      "created_at": "...",
      "status": "succeeded"
    }
  ]
}
```

### `GET /health`

**Purpose.** Service health + active provider type. Never returns secret values.

**Response:**
```json
{
  "status": "ok",
  "provider": "nim",
  "version": "0.1.0"
}
```

## Authentication

Phase 1: single-user local deployment. No auth layer. `.env`
credentials never leave host. Phase 2 may add host-level access
control/config boundary rather than app auth.
