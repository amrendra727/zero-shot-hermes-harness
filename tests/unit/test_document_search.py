"""Tests for local document search API."""
from __future__ import annotations

from pathlib import Path

import pytest
from docx import Document

from src.api.document_search import search_documents


def _write_docx(path: Path, text: str) -> None:
    doc = Document()
    doc.add_paragraph(text)
    doc.save(path)


def test_document_search_rejects_empty_query(tmp_path: Path) -> None:
    with pytest.raises(Exception) as exc:
        search_documents(type("Req", (), {"query": "   ", "root": str(tmp_path), "max_results": 5})())
    detail = exc.value.detail
    assert detail["code"] == "bad_request"
    assert exc.value.status_code == 400


def test_document_search_rejects_bad_root() -> None:
    with pytest.raises(Exception) as exc:
        search_documents(type("Req", (), {"query": "alpha", "root": "/bad-root-xyz", "max_results": 5})())
    detail = exc.value.detail
    assert detail["code"] == "bad_root"
    assert exc.value.status_code == 400


def test_document_search_matches_docx(tmp_path: Path) -> None:
    target = tmp_path / "report.docx"
    _write_docx(target, "UP Police zone review monthly summary alpha bravo.")
    root = str(tmp_path)

    response = search_documents(type("Req", (), {"query": "alpha", "root": root, "max_results": 10})())
    data = response["data"]
    assert data["count"] == 1
    assert data["results"][0]["filename"] == "report.docx"
    assert "alpha" in data["results"][0]["snippet"]
    assert data["results"][0]["score"] > 0


def test_document_search_matches_doc_best_effort(tmp_path: Path) -> None:
    doc = tmp_path / "legacy.doc"
    doc.write_bytes(b"UP Police zone review monthly summary charlie delta.")

    response = search_documents(type("Req", (), {"query": "charlie", "root": str(tmp_path), "max_results": 10})())
    data = response["data"]
    assert data["count"] == 1
    assert data["results"][0]["filename"] == "legacy.doc"
