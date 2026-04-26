"""Tests for native PDF extraction (P3).

`extract_pdf_text` tries Docling first (OCR off for speed), falls back
to pypdf when Docling is unavailable or fails.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

_office = importlib.import_module("my_llm_wiki.detect-office-convert")
_docling = importlib.import_module("my_llm_wiki.extract-with-docling")


def _make_minimal_pdf(path: Path) -> None:
    """Create a tiny native PDF with embedded text (no OCR needed)."""
    try:
        from reportlab.pdfgen import canvas
    except ImportError:
        pytest.skip("reportlab not installed")
    c = canvas.Canvas(str(path))
    c.drawString(72, 720, "Hello PDF")
    c.drawString(72, 700, "Second line of native text.")
    c.showPage()
    c.save()


def test_pdf_native_falls_back_to_pypdf_when_docling_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf = tmp_path / "fallback.pdf"
    _make_minimal_pdf(pdf)
    monkeypatch.setattr(_docling, "is_docling_available", lambda: False)
    text = _office.extract_pdf_text(pdf)
    assert "Hello PDF" in text


def test_pdf_native_uses_docling_when_available(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    if not _docling.is_docling_available():
        pytest.skip("docling not installed")
    pdf = tmp_path / "withdocling.pdf"
    _make_minimal_pdf(pdf)

    calls: list = []
    real_extract = _docling.extract_with_docling

    def spy(p):
        calls.append(p)
        return real_extract(p)

    monkeypatch.setattr(_office, "_docling_extract", spy, raising=False)
    text = _office.extract_pdf_text(pdf)
    assert "Hello PDF" in text
    assert len(calls) == 1


def test_pdf_returns_empty_for_nonexistent_file(tmp_path: Path) -> None:
    text = _office.extract_pdf_text(tmp_path / "missing.pdf")
    assert text == ""
