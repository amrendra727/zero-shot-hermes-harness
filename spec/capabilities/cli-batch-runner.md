
# Capability: CLI + Batch Runner

## What It Does

Provide CLI entry points and a scheduled batch runner so analysts can
run predefined questions against a workspace without a browser.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| workspace_id | string | CLI arg/env | Yes |
| question | string | file/stdin | Yes |
| output | string | CLI flag | No |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| run result | object | stdout / file |
| artifact path | string | filesystem |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Same core runtime as web | reuse agent runtime | same errors as API |

## Business Rules

- Batch mode writes outputs to a configured directory.
- No interactive prompts in batch mode unless `--interactive` is passed.

## Success Criteria

- [ ] `uv run python -m src --help` shows available commands.
- [ ] Batch job runs headlessly and writes output artifact.
- [ ] Nonzero exit on unrecoverable failure.
