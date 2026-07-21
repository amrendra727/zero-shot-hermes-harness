
# Capability: NL Q&A + Evidence Rendering

## What It Does

Answer a plain-language police-data question in the current workspace,
returning natural-language text, a table, ranked lists, chart metadata,
a downloadable artifact suggestion, and a SQL suggestion the user can
inspect or request to run.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| workspace_id | string | session state | Yes |
| question | string | user input | Yes |
| insights_toggle | boolean | UI toggle | No |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| answer | string | UI / API |
| table | object | UI / API |
| chart_spec | object | UI |
| sql_suggestion | string | UI expander |
| follow_ups | list[string] | UI, insights only |
| anomalies | list[string] | UI, insights only |
| report_artifact_path | string | download endpoint |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| NVIDIA NIM | completion for planning and NL generation | 401/429 → readable error |

## Business Rules

- Default mode is answer-only with expandable internals.
- insights_toggle=True enables follow-ups and anomaly flags.
- SQL suggestion is parameterized and read-only only.
- Ranked lists are sorted by computed value descending unless asked
  otherwise.

## Success Criteria

- [ ] Question produces a response with `answer` populated.
- [ ] insights_toggle=False hides follow-ups/anomalies.
- [ ] insights_toggle=True includes at least one follow-up or anomaly
      when data supports it.
