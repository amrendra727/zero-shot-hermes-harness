"""add workspace metadata tables"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "0001_add_workspace_metadata_tables"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS workspace (
                id TEXT NOT NULL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                owner TEXT,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS dataset (
                id TEXT NOT NULL PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                name TEXT NOT NULL,
                source_filename TEXT NOT NULL,
                mime_type TEXT NOT NULL DEFAULT 'text/csv',
                storage_path TEXT,
                row_count INTEGER,
                column_count INTEGER,
                checksum TEXT,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS artifact (
                id TEXT NOT NULL PRIMARY KEY,
                dataset_id TEXT,
                run_id TEXT,
                kind TEXT NOT NULL DEFAULT 'file',
                filename TEXT,
                mime_type TEXT,
                storage_path TEXT,
                byte_size INTEGER,
                meta TEXT,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    op.execute(text("CREATE INDEX IF NOT EXISTS ix_dataset_workspace_id ON dataset (workspace_id)"))
    op.execute(text("CREATE INDEX IF NOT EXISTS ix_artifact_dataset_id ON artifact (dataset_id)"))
    op.execute(text("CREATE INDEX IF NOT EXISTS ix_artifact_run_id ON artifact (run_id)"))


def downgrade() -> None:
    op.execute(text("DROP INDEX IF EXISTS ix_artifact_run_id"))
    op.execute(text("DROP INDEX IF EXISTS ix_artifact_dataset_id"))
    op.execute(text("DROP INDEX IF EXISTS ix_dataset_workspace_id"))
    op.execute(text("DROP TABLE IF EXISTS artifact"))
    op.execute(text("DROP TABLE IF EXISTS dataset"))
    op.execute(text("DROP TABLE IF EXISTS workspace"))
