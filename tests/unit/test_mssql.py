"""Tests for MsSQL provider read-only policy and provider resolution."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.llm.providers.mssql import MsSQLProvider


def test_no_connection_string_raises() -> None:
    with pytest.raises(Exception):
        MsSQLProvider(connection_string="")


def test_read_only_blocks_write_queries() -> None:
    provider = MsSQLProvider(connection_string="DRIVER={SQL Server};SERVER=x;DATABASE=y;", read_only=True)
    with pytest.raises(Exception):
        provider.execute("INSERT INTO dbo.x (a) VALUES (1)")


@patch("pyodbc.connect")
def test_read_select_allowed_by_policy(mock_connect: MagicMock) -> None:
    mock_cursor = MagicMock()
    mock_cursor.description = [("test",)]
    mock_cursor.fetchall.return_value = [(1,)]
    mock_connection = MagicMock()
    mock_connection.cursor.return_value = mock_cursor
    mock_connection.__enter__.return_value = mock_connection
    mock_cursor.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_connection

    provider = MsSQLProvider(connection_string="DRIVER={SQL Server};SERVER=x;DATABASE=y;", read_only=True)
    rows = provider.execute("SELECT 1 AS test")

    assert rows == [{"test": 1}]
    mock_connect.assert_called_once()
    mock_connection.rollback.assert_called_once()


def test_complete_raises() -> None:
    provider = MsSQLProvider(connection_string="DRIVER={SQL Server};SERVER=x;DATABASE=y;")
    with pytest.raises(Exception):
        provider.complete("sys", "user")
