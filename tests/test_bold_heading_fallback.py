"""Tests for bold-as-heading fallback (D7).

When a document has zero markdown # headings but uses standalone bold lines
(e.g. **TITLE** on its own line) as section markers, treat each qualifying
bold line as an h1 heading. Surfaced by the v0.7 E2E real-corpus test.

Heuristic: only kicks in when no ``#``-style headings exist. A qualifying
bold line is a standalone ``**...**`` (2-80 chars) with no trailing
punctuation (., , : ; ? !), evaluated outside fenced code blocks.
"""
from __future__ import annotations

import importlib
from pathlib import Path

_extract_docs = importlib.import_module("my_llm_wiki.extract-docs")


def test_bold_lines_become_headings_when_no_hash_headings(tmp_path: Path) -> None:
    md = tmp_path / "doc.md"
    md.write_text(
        "**TRUYỆN KIỀU**\n\n"
        "Body paragraph here.\n\n"
        "**I**\n\n"
        "Section one body.\n\n"
        "**II**\n\n"
        "Section two body.\n",
        encoding="utf-8",
    )
    result = _extract_docs.extract_doc(md)
    titles = [n["label"] for n in result["nodes"] if n["label"] != "doc"]
    assert "TRUYỆN KIỀU" in titles
    assert "I" in titles
    assert "II" in titles


def test_hash_headings_take_precedence_over_bold(tmp_path: Path) -> None:
    """When real # headings exist, bold lines must NOT be promoted —
    avoid double-counting."""
    md = tmp_path / "doc.md"
    md.write_text(
        "# Real Heading\n\n"
        "**Should Not Become Heading**\n\n"
        "Body.\n",
        encoding="utf-8",
    )
    result = _extract_docs.extract_doc(md)
    titles = [n["label"] for n in result["nodes"] if n["label"] != "doc"]
    assert "Real Heading" in titles
    assert "Should Not Become Heading" not in titles


def test_bold_with_trailing_punctuation_rejected(tmp_path: Path) -> None:
    """Sentences ending with bold ('I love **Paris**.') aren't headings."""
    md = tmp_path / "doc.md"
    md.write_text(
        "**This sentence ends with a period.**\n\n"
        "**Question?**\n\n"
        "**Listed item:**\n\n"
        "**Valid Heading**\n",
        encoding="utf-8",
    )
    result = _extract_docs.extract_doc(md)
    titles = [n["label"] for n in result["nodes"] if n["label"] != "doc"]
    assert "Valid Heading" in titles
    assert "This sentence ends with a period." not in titles
    assert "Question?" not in titles
    assert "Listed item:" not in titles


def test_bold_inline_within_paragraph_rejected(tmp_path: Path) -> None:
    """Bold inside a paragraph (not standalone on its own line) is not a heading."""
    md = tmp_path / "doc.md"
    md.write_text(
        "Some intro text with **bold inline** in the middle.\n\n"
        "**Standalone Heading**\n",
        encoding="utf-8",
    )
    result = _extract_docs.extract_doc(md)
    titles = [n["label"] for n in result["nodes"] if n["label"] != "doc"]
    assert "Standalone Heading" in titles
    assert "bold inline" not in titles


def test_bold_too_long_rejected(tmp_path: Path) -> None:
    """Bold lines >80 chars are likely a quoted/emphasized paragraph, not a heading."""
    long = "X" * 100
    md = tmp_path / "doc.md"
    md.write_text(
        f"**{long}**\n\n"
        "**Short Title**\n",
        encoding="utf-8",
    )
    result = _extract_docs.extract_doc(md)
    titles = [n["label"] for n in result["nodes"] if n["label"] != "doc"]
    assert "Short Title" in titles
    assert long not in titles


def test_cross_doc_edges_via_bold_headings(tmp_path: Path) -> None:
    """Two docs sharing a bold-as-heading title should get a same_concept edge."""
    (tmp_path / "doc_a.md").write_text(
        "**Truyện Kiều**\n\nVăn chương Việt Nam.\n",
        encoding="utf-8",
    )
    (tmp_path / "doc_b.md").write_text(
        "**Truyện Kiều**\n\nNguyễn Du.\n",
        encoding="utf-8",
    )
    result = _extract_docs.extract_docs(
        [tmp_path / "doc_a.md", tmp_path / "doc_b.md"], root=tmp_path
    )
    same_concept = [
        e for e in result["edges"] if e.get("relation") == "same_concept"
    ]
    assert len(same_concept) >= 1
