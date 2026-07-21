
# UI — UP Police Data Analyst

## UI Type

Web dashboard served at `/app` from the FastAPI backend.

## Views / Screens

### Screen: Workspace list

**Purpose.** Choose or create an investigation workspace.

**Key elements:**
- Workspace list/table
- Create workspace form

**Actions available:**
- Create workspace
- Open workspace

### Screen: Workspace detail

**Purpose.** Query and inspect results within one workspace.

**Key elements:**
- Dataset upload panel
- Question input
- Answer panel
- Table viewer
- Chart viewer
- SQL expander
- Steps/trail expander
- Follow-up suggestions
- Artifact download controls

**Actions available:**
- Upload CSV
- Ask question
- Toggle insights
- Download report/output
- Copy SQL

## Error States

- Schema ambiguity: show inferred types + allow manual override.
- Empty result: show “no rows match this question.”
- Provider failure: show retry action with degraded guidance.
- Upload failure: show file parse error + row/column hints.

## Tech Stack

Zero-build static frontend: `frontend/public/` — `index.html`,
`styles.css`, `app.js`. No npm/build step in Phase 1.
