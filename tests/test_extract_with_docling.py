"""Tests for Docling adapter (P1).

The adapter wraps Docling behind a stable internal API. It must:
- Detect availability at runtime via `is_docling_available()`
- Return a normalized dict shape from `extract_with_docling(path)`
- Never raise on missing Docling — return error dict instead
- Never expose Docling-specific types upward
"""
from __future__ import annotations

from pathlib import Path

import pytest

from my_llm_wiki import extract_with_docling, is_docling_available


def test_is_docling_available_returns_bool() -> None:
    result = is_docling_available()
    assert isinstance(result, bool)


def test_extract_returns_error_for_nonexistent_file(tmp_path: Path) -> None:
    missing = tmp_path / "nope.pdf"
    result = extract_with_docling(missing)
    assert isinstance(result, dict)
    assert result.get("error")  # truthy error message


def test_extract_returns_expected_keys(tmp_path: Path) -> None:
    if not is_docling_available():
        pytest.skip("docling not installed")
    # minimal HTML — Docling handles it without ML downloads
    sample = tmp_path / "sample.html"
    sample.write_text(
        "<html><body><h1>Title</h1><p>Body text here.</p></body></html>",
        encoding="utf-8",
    )
    result = extract_with_docling(sample)
    assert "text" in result
    assert "headings" in result
    assert "tables" in result
    assert "page_count" in result
    assert "error" in result
    assert result["error"] is None
    assert "Title" in result["text"]


def test_extract_returns_error_dict_when_docling_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Force the unavailable path even when docling is installed, by monkeypatching the check."""
    import importlib
    mod = importlib.import_module("my_llm_wiki.extract-with-docling")
    monkeypatch.setattr(mod, "is_docling_available", lambda: False)

    sample = tmp_path / "x.html"
    sample.write_text("<p>hi</p>", encoding="utf-8")
    result = mod.extract_with_docling(sample)
    assert result["error"]
    assert "docling" in result["error"].lower()
