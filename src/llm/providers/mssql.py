"""Microsoft SQL Server provider — read-only query adapter over pyodbc."""
from __future__ import annotations

from typing import Any

import pyodbc

from src.llm.providers.base import LLMError, LLMProvider


class MsSQLProvider(LLMProvider):
    name = "mssql"
    default_model = ""

    def __init__(
        self,
        connection_string: str,
        model: str | None = None,
        read_only: bool = True,
    ) -> None:
        if not connection_string:
            raise LLMError("Missing MsSQL connection string.")
        self.connection_string = connection_string
        self.model = model or self.default_model
        self.read_only = read_only

    @staticmethod
    def _looks_write(statement: str) -> bool:
        shard = statement.lstrip().split(" ", 1)[0].lower()
        return shard in {"insert", "update", "delete", "merge", "truncate", "alter", "drop", "create"}

    def complete(self, system: str, user: str, *, max_tokens: int = 1024) -> str:
        raise LLMError("MsSQLProvider is a source adapter only. Use an LLM provider for generation.")

    def execute(self, query: str) -> list[dict[str, object]]:
        if self.read_only and self._looks_write(query):
            raise LLMError("Read-only policy blocked a write-style statement.")
        try:
            with pyodbc.connect(self.connection_string, autocommit=False) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    if cursor.description is None:
                        conn.rollback()
                        return []
                    columns = [desc[0] for desc in cursor.description]
                    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    conn.rollback()
                    return rows
        except pyodbc.Error as exc:
            raise LLMError(f"MsSQL query failed: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"MsSQL execution error: {exc}") from exc
