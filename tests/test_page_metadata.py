"""Tests for page metadata on PDF document nodes (P6).

PDF-derived hub nodes carry a `pages` attribute when Docling reports a
page_count. Other document types (md, docx, html) have no concept of
pages and the attribute is absent.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

_extract_docs = importlib.import_module("my_llm_wiki.extract-docs")
_docling = importlib.import_module("my_llm_wiki.extract-with-docling")


def _make_pdf(path: Path, n_pages: int = 2) -> None:
    try:
        from reportlab.pdfgen import canvas
    except ImportError:
        pytest.skip("reportlab not installed")
    c = canvas.Canvas(str(path))
    for i in range(n_pages):
        c.drawString(72, 720, f"Page {i + 1} of test PDF")
        c.showPage()
    c.save()


def test_pdf_hub_node_has_pages_attribute(tmp_path: Path) -> None:
    if not _docling.is_docling_available():
        pytest.skip("docling not installed")
    pdf = tmp_path / "doc.pdf"
    _make_pdf(pdf, n_pages=3)
    result = _extract_docs.extract_doc(pdf)
    nodes = result["nodes"]
    assert nodes, "expected at least the hub node"
    hub = next((n for n in nodes if n.get("file_type") == "paper"), None)
    assert hub is not None
    assert "pages" in hub
    assert hub["pages"] == 3


def test_markdown_hub_node_has_no_pages(tmp_path: Path) -> None:
    md = tmp_path / "doc.md"
    md.write_text("# Title\n\nBody.\n", encoding="utf-8")
    result = _extract_docs.extract_doc(md)
    nodes = result["nodes"]
    hub = next((n for n in nodes if n.get("file_type") == "document"), None)
    assert hub is not None
    assert "pages" not in hub
