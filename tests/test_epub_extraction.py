"""Tests for EPUB extraction (D8).

EPUB is the most common ebook format. Docling 2.91 has no native EPUB
support, but EPUB is structurally a ZIP of XHTML documents — we unzip,
concatenate chapter HTML in spine order, and feed the merged HTML to
Docling's HTML pipeline. v0.7 silently dropped .epub files; v0.8 wires
them through `convert_office_file` via this two-step path.
"""
from __future__ import annotations

import importlib
import zipfile
from pathlib import Path
from unittest.mock import patch

_office = importlib.import_module("my_llm_wiki.detect-office-convert")
_detect = importlib.import_module("my_llm_wiki.detect-files")


def _make_minimal_epub(path: Path, chapter_html: str = "<html><body><h1>Chapter 1</h1><p>Once upon a time.</p></body></html>") -> None:
    """Build a minimal valid EPUB at `path` for tests."""
    container_xml = (
        '<?xml version="1.0"?>'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles>'
        '</container>'
    )
    opf = (
        '<?xml version="1.0"?>'
        '<package xmlns="http://www.idpf.org/2007/opf" version="2.0">'
        '<manifest>'
        '<item id="ch1" href="ch1.html" media-type="application/xhtml+xml"/>'
        '</manifest>'
        '<spine><itemref idref="ch1"/></spine>'
        '</package>'
    )
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", container_xml)
        z.writestr("content.opf", opf)
        z.writestr("ch1.html", chapter_html)


def test_epub_in_office_extensions() -> None:
    """EPUB must be classified as an office-convertible file type so the
    pipeline routes it through `convert_office_file`."""
    assert ".epub" in _detect.OFFICE_EXTENSIONS


def test_epub_classified_as_document(tmp_path: Path) -> None:
    """An .epub file in a corpus should be classified as DOCUMENT — the
    OFFICE_EXTENSIONS bucket maps to FileType.DOCUMENT and triggers
    conversion to markdown sidecar."""
    epub = tmp_path / "book.epub"
    _make_minimal_epub(epub)
    ftype = _detect.classify_file(epub)
    assert ftype == _detect.FileType.DOCUMENT


def test_epub_unzip_extracts_chapter_html(tmp_path: Path) -> None:
    """The pure-stdlib EPUB-to-HTML step must unpack chapters in spine order
    and return a single concatenated HTML body. No Docling involved."""
    epub = tmp_path / "book.epub"
    _make_minimal_epub(
        epub,
        chapter_html="<html><body><h1>Phần Một</h1><p>Văn Việt.</p></body></html>",
    )
    html = _office._epub_to_html(epub)
    assert "Phần Một" in html
    assert "Văn Việt" in html


def test_epub_to_markdown_uses_docling(tmp_path: Path) -> None:
    """epub_to_markdown must delegate to Docling and return its text."""
    epub = tmp_path / "book.epub"
    _make_minimal_epub(epub)
    fake_result = {
        "text": "# Chapter 1\n\nOnce upon a time.",
        "headings": [], "tables": [], "page_count": 0,
    }
    with patch.object(_office, "_docling_extract", return_value=fake_result), \
         patch.object(_office._docling, "is_docling_available", return_value=True):
        text = _office.epub_to_markdown(epub)
    assert "Chapter 1" in text
    assert "Once upon a time" in text


def test_epub_to_markdown_returns_empty_when_docling_unavailable(tmp_path: Path) -> None:
    """No fallback: when Docling isn't installed, EPUB returns empty (skipped)."""
    epub = tmp_path / "book.epub"
    _make_minimal_epub(epub)
    with patch.object(_office._docling, "is_docling_available", return_value=False):
        text = _office.epub_to_markdown(epub)
    assert text == ""


def test_epub_to_markdown_returns_empty_on_docling_error(tmp_path: Path) -> None:
    """Docling errors should be swallowed — file is skipped, not crashing."""
    epub = tmp_path / "book.epub"
    _make_minimal_epub(epub)
    fake_result = {"text": "", "headings": [], "tables": [], "page_count": 0, "error": "boom"}
    with patch.object(_office, "_docling_extract", return_value=fake_result), \
         patch.object(_office._docling, "is_docling_available", return_value=True):
        text = _office.epub_to_markdown(epub)
    assert text == ""


def test_convert_office_file_dispatches_epub(tmp_path: Path) -> None:
    """convert_office_file must route .epub through epub_to_markdown and
    write a sidecar .md in out_dir."""
    epub = tmp_path / "book.epub"
    _make_minimal_epub(epub)
    out_dir = tmp_path / "converted"
    fake_result = {
        "text": "**Book Title**\n\nFirst paragraph.",
        "headings": [], "tables": [], "page_count": 0,
    }
    with patch.object(_office, "_docling_extract", return_value=fake_result), \
         patch.object(_office._docling, "is_docling_available", return_value=True):
        out_path = _office.convert_office_file(epub, out_dir)
    assert out_path is not None
    assert out_path.suffix == ".md"
    content = out_path.read_text(encoding="utf-8")
    assert "Book Title" in content
    assert "converted from book.epub" in content
