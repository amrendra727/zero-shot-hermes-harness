
# Capability: CSV Workspace Ingestion

## What It Does

Upload one or more CSV files into a named investigation workspace,
infer schema, and make the dataset available for question answering.

## Inputs

| Input | Type | Source | Required |
|-------|------|--------|----------|
| workspace_id | string | URL/path | Yes |
| file | UploadFile | multipart upload | Yes |
| title | string | form field | No |

## Outputs

| Output | Type | Destination |
|--------|------|-------------|
| dataset_id | string | DB |
| filename | string | DB |
| columns | list[object] | API response |
| row_count | integer | API response |
| status | string | API response |

## External Calls

| System | Operation | On Failure |
|--------|-----------|------------|
| Filesystem / stdio | read uploaded multipart file | 413/422 response |

## Business Rules

- Accepted formats: `.csv` only in Phase 1.
- Maximum 1 GB per file.
- A workspace can hold multiple datasets, but primary questions run
  against the most recently active dataset unless the user selects one.

## Success Criteria

- [ ] Upload returns dataset metadata within 2 seconds for <50 MB.
- [ ] Upload returns 413 for files >1 GB.
- [ ] Schema inference exposes at least column names and type guesses.
