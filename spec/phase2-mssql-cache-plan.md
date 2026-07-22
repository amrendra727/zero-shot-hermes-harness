# Phase 2 Plan — MsSQL Integration + Query Cache Layer

## Objective

Add a live MsSQL data source to the analyst agent with read-only access,
parameterized queries, and a lightweight cache layer. Keep DB load low,
latency feel instant, and data boundary local-only.

## Scope

- MsSQL read-only provider module
- Connection-pool configuration with credential-local `.env` fields only
- Query cache / summarized view layer
- CLI + batch runner entry points

## Out of Scope

- Auth changes, write-back paths, multi-language, mobile

## Key Files

- `src/llm/providers/mssql.py` — new provider
- `src/db/session.py` — add MsSQL engine/session path + cache config hooks
- `src/config/settings.py` — `.env` fields for MsSQL access only
- `src/graph/nodes.py` — extend `select_source` / `execute_query` for `mssql`
- `scripts/` — batch job runner
- `tests/` — integration target for `mssql` slice

## MsSQL Provider Rules

- Read-only only
- Parameterized queries only
- Preferred data path: cached summary tables refreshed by DBA
- No write/DDL from agent runtime

## Cache Layer Rules

- Cache summarized results by stable query signature + source fingerprint
- Serve cached result when within TTL
- Invalidate on signal/configured window or explicit workspace refresh

## `.env` Contract

- `MSSQL_CONNECTION_STRING` or DSN template
- `MSSQL_READ_ONLY=1`
- No secrets committed; no telemetry exfil
