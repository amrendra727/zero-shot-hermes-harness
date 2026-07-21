
# Roadmap — UP Police Data Analyst Agent

## Purpose

A narrow, domain-specific analyst agent for the UP Police. It ingests
police-domain CSV exports and live MsSQL data, answers natural-language
questions, and returns plain-language answers, tables, charts, ranked
lists, downloadable outputs, and SQL suggestions. It is built for
occasional ad-hoc use, review-meeting walkthroughs, zone-level analyst
runs, and overnight batch jobs.

## Who Uses It

- Station in-charge during crime-review meetings.
- Analysts working across a range/zone.
- Overnight batch runs producing scheduled outputs.

## Success Criteria

- A non-technical user can paste or upload a CSV, type a question in
  plain English, and receive a correct answer with supporting evidence
  in under 10 seconds for small inputs.
- A user can return to an earlier workspace and see prior questions,
  answers, and files.
- A user can switch from a CSV workspace to a live MsSQL workspace
  without leaving the app.
- Advanced queries produce SQL suggestions the user can inspect, copy,
  or request explain.

## Core Constraints

- Data/results never leave the APBN/MP machine/network boundary.
- Provider key stays local in `.env`; no external credential sync.
- Inference cost is hidden from the user; vectorized/minimal LLM usage.
- Live MsSQL access is read-only; no write-back from the agent.

## Out of Scope

- User auth, role-based access control, SSO.
- Incident/fIR writeback into MsSQL.
- Multi-language translation beyond question/answer IO.
- Mobile app.

---

## Phases of Development

### Phase 1 — CSV Workspace + NL Q&A (smallest first-time-right win)

**Goal.** Upload CSV(s), ask questions in plain English, get answers,
tables, charts, ranked lists, downloadable reports, and SQL suggestions;
revisit the workspace later.

**Independent slices.**
- CSV ingestion + schema inference
- Workspace persistence
- NL-to-SQL/reasoning node + answer renderer
- API + frontend surfaces

**Key surfaces/files.**
- `src/graph/nodes.py`: `transform_text` becomes `analyse_question`
- `src/prompts/transform.md` → `src/prompts/analyst.md`
- `src/api/runs.py` extensions for workspace CRUD + result streaming
- `frontend/public/` new upload + workspace view
- `tests/unit/`, `tests/integration/`

**Gate.**
```bash
uv sync
cp .env.example .env
uv run pytest tests/unit -q
uv run python agent.py --run &
for i in {1..20}; do curl -sf http://localhost:8001/health && break || sleep 2; done
curl -sf http://localhost:8001/app/ > /dev/null
uv run pytest tests/integration -q
```
Real LLM/API via `.env`; NIM provider call must return 200.

**How the user tests it.**
1. Open the app; upload one CSV.
2. Ask: "Top 5 stations by total incidents."
3. Expect NL answer + table + chart + SQL suggestion in one response.

---

### Phase 2 — MsSQL + Query Cache + Batch Access

**Goal.** Connect workspace data source to a live MsSQL instance using
cached summarized views and low-load query patterns; add CLI + batch
job access.

**Independent slices.**
- MsSQL read-only provider with connection-pool/cache controls
- Query plan cache / materialized summary layer
- CLI entry point
- Scheduled batch job runner

**Key surfaces/files.**
- `src/llm/providers/mssql.py`
- `src/db/session.py` extension for MsSQL + cache config
- `src/domain/run.py` extensions for source switching
- `scripts/` batch runner
- CLI endpoint

**Gate.**
```bash
uv run pytest tests/integration -q -k "mssql"
uv run python agent.py --run &
for i in {1..20}; do curl -sf http://localhost:8001/health && break || sleep 2; done
# Batch job runner self-test
uv run python scripts/batch_job.py --help
```

**How the user tests it.**
1. Configure MsSQL connection template in `.env`.
2. Start app; switch source from CSV to MsSQL.
3. Ask same question; expect answer from DB with same UI.
