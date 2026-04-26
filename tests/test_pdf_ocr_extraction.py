"""Tests for OCR fallback on scanned PDFs (P4).

When the native (text-based) extraction yields very little text but the
PDF clearly has pages, treat it as scanned and re-run Docling with OCR.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

_office = importlib.import_module("my_llm_wiki.detect-office-convert")
_docling = importlib.import_module("my_llm_wiki.extract-with-docling")


def _make_text_pdf(path: Path) -> None:
    try:
        from reportlab.pdfgen import canvas
    except ImportError:
        pytest.skip("reportlab not installed")
    c = canvas.Canvas(str(path))
    c.drawString(72, 720, "Native text content here.")
    c.showPage()
    c.save()


def test_looks_scanned_true_for_empty_text() -> None:
    assert _office._looks_scanned("", page_count=3) is True


def test_looks_scanned_false_for_substantial_text() -> None:
    assert _office._looks_scanned("This is a long enough chunk of text " * 10, page_count=2) is False


def test_looks_scanned_false_for_single_page_with_some_text() -> None:
    # A title-only PDF should NOT trigger expensive OCR
    assert _office._looks_scanned("Title", page_count=1) is False


def test_ocr_skipped_when_native_succeeds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    if not _docling.is_docling_available():
        pytest.skip("docling not installed")
    pdf = tmp_path / "native.pdf"
    _make_text_pdf(pdf)

    ocr_calls: list = []

    def fake_ocr(p):
        ocr_calls.append(p)
        return {"text": "OCR'd text", "headings": [], "tables": [], "page_count": 1, "error": None}

    monkeypatch.setattr(_office, "_docling_extract_with_ocr", fake_ocr, raising=False)
    text = _office.extract_pdf_text(pdf)
    assert "Native text content here" in text
    assert len(ocr_calls) == 0, "OCR must not run when native extraction succeeded"


def test_ocr_triggered_when_native_yields_no_text(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    if not _docling.is_docling_available():
        pytest.skip("docling not installed")
    pdf = tmp_path / "scanned.pdf"
    _make_text_pdf(pdf)

    # Force native paths to return empty so OCR fallback engages
    def empty_extract(p):
        return {"text": "", "headings": [], "tables": [], "page_count": 3, "error": None}

    ocr_calls: list = []

    def fake_ocr(p):
        ocr_calls.append(p)
        return {"text": "OCR'd text from scan", "headings": [], "tables": [], "page_count": 3, "error": None}

    monkeypatch.setattr(_office, "_docling_extract", empty_extract, raising=False)
    monkeypatch.setattr(_office, "_docling_extract_with_ocr", fake_ocr, raising=False)
    # Make the pypdf fallback also yield empty so we definitely hit OCR
    monkeypatch.setattr(_office, "_pypdf_extract", lambda p: "", raising=False)

    text = _office.extract_pdf_text(pdf)
    assert "OCR'd text from scan" in text
    assert len(ocr_calls) == 1
