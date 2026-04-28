"""Tests for cmd_stale_refs in query-graph.py (TDD red→green).

Fixture: in-memory vault with notes containing [[ExistingNode]] and [[GhostNode]].
cmd_stale_refs must return (file, line_number, "GhostNode") entries for missing refs
and nothing for refs that resolve to a node label in the graph.

Edge cases:
- References inside fenced code blocks (``` ... ```) must be ignored.
- Same-line multiple wikilinks: each checked independently.
- Section anchors like [[Foo#Bar]] normalised to "Foo".
"""
from __future__ import annotations

import importlib
from pathlib import Path

import networkx as nx
import pytest

_query = importlib.import_module("my_llm_wiki.query-graph")
cmd_stale_refs = _query.cmd_stale_refs


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_graph(labels: list[str]) -> nx.Graph:
    G = nx.Graph()
    for i, lbl in enumerate(labels):
        G.add_node(f"n{i}", label=lbl, file_type="code")
    return G


def _write_vault(tmp_path: Path, notes: dict[str, str]) -> Path:
    """Write a dict of filename → content into tmp_path/vault/ and return vault dir."""
    vault = tmp_path / "vault"
    vault.mkdir()
    for name, content in notes.items():
        (vault / name).write_text(content, encoding="utf-8")
    return vault


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_stale_refs_detects_missing_node(tmp_path: Path) -> None:
    """[[GhostNode]] not in graph → reported as stale."""
    vault = _write_vault(tmp_path, {
        "note.md": "Some text [[ExistingNode]] and [[GhostNode]] here.\n",
    })
    G = _make_graph(["ExistingNode"])
    result = cmd_stale_refs(G, vault)
    assert "GhostNode" in result


def test_stale_refs_ignores_valid_ref(tmp_path: Path) -> None:
    """[[ExistingNode]] present in graph → NOT reported."""
    vault = _write_vault(tmp_path, {
        "note.md": "Reference to [[ExistingNode]].\n",
    })
    G = _make_graph(["ExistingNode"])
    result = cmd_stale_refs(G, vault)
    assert "ExistingNode" not in result


def test_stale_refs_reports_file_and_line(tmp_path: Path) -> None:
    """Result must contain the file name and line number of the stale ref."""
    vault = _write_vault(tmp_path, {
        "broken.md": "line1\n[[Missing]] here\nline3\n",
    })
    G = _make_graph([])
    result = cmd_stale_refs(G, vault)
    assert "broken.md" in result
    assert "Missing" in result
    # Line 2 is where the ref appears
    assert "2" in result


def test_stale_refs_skips_fenced_code_blocks(tmp_path: Path) -> None:
    """Wikilinks inside fenced code blocks must be ignored."""
    content = (
        "Normal text [[RealRef]].\n"
        "```\n"
        "[[FakeRef]] inside code block — should be ignored\n"
        "```\n"
        "After fence [[AnotherGhost]].\n"
    )
    vault = _write_vault(tmp_path, {"mixed.md": content})
    G = _make_graph(["RealRef"])
    result = cmd_stale_refs(G, vault)
    assert "FakeRef" not in result
    assert "AnotherGhost" in result


def test_stale_refs_empty_vault(tmp_path: Path) -> None:
    """Vault with no .md files → empty output, no error."""
    vault = tmp_path / "vault"
    vault.mkdir()
    G = _make_graph(["Alpha"])
    result = cmd_stale_refs(G, vault)
    # No stale refs — summary should say 0
    assert "0" in result


def test_stale_refs_multiple_in_one_line(tmp_path: Path) -> None:
    """Multiple wikilinks on one line: each checked independently."""
    vault = _write_vault(tmp_path, {
        "multi.md": "See [[Good]] and [[Bad1]] plus [[Bad2]].\n",
    })
    G = _make_graph(["Good"])
    result = cmd_stale_refs(G, vault)
    assert "Bad1" in result
    assert "Bad2" in result
    assert "Good" not in result


def test_stale_refs_section_anchor_normalised(tmp_path: Path) -> None:
    """[[Node#Section]] should resolve against 'Node' label only."""
    vault = _write_vault(tmp_path, {
        "anchors.md": "See [[ExistingNode#details]] and [[GhostNode#intro]].\n",
    })
    G = _make_graph(["ExistingNode"])
    result = cmd_stale_refs(G, vault)
    assert "GhostNode" in result
    assert "ExistingNode" not in result


def test_stale_refs_no_stale(tmp_path: Path) -> None:
    """All refs resolve → output contains 0 stale refs."""
    vault = _write_vault(tmp_path, {
        "clean.md": "See [[Alpha]] and [[Beta]].\n",
    })
    G = _make_graph(["Alpha", "Beta"])
    result = cmd_stale_refs(G, vault)
    assert "Alpha" not in result
    assert "Beta" not in result
    assert "0" in result
