
# Capability: Workspace Persistence + History

## What It Does

Persist workspaces, datasets, runs, and artifacts so a user can return
to prior investigations, prior questions and answers.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| workspace_id | string | session/route | Yes |
| run_id | string | session/route | No |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| workspace list | list[object] | UI/API |
| run history | list[object] | UI/API |
| artifact URL | string | download endpoint |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| SQLAlchemy/SQLite | persist lookup | retry / show empty state |

## Business Rules

- A workspace is scoped to local deployment in Phase 1.
- Deleting a workspace removes datasets, runs, and artifacts.

## Success Criteria

- [ ] Creating a workspace makes it visible in workspace list.
- [ ] Asking a question appends a run entry visible in history.
- [ ] Artifact download returns file content for the correct run_id.
