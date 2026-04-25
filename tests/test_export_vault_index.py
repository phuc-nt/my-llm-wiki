"""Tests for vault/index.md generation (A1 from future-enhancements-backlog).

The index.md is a content catalog grouped by file_type + a Communities section.
LLMs read this first to navigate the vault efficiently (Karpathy pattern).
"""
from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest

from my_llm_wiki import to_vault


def _build_sample_graph() -> tuple[nx.Graph, dict[int, list[str]], dict[int, str], dict[int, float]]:
    """Sample graph with 2 communities, mixed file_types."""
    G = nx.Graph()
    G.add_node("c1", label="GraphStore", file_type="code", source_file="src/store.py")
    G.add_node("c2", label="indexBy", file_type="code", source_file="src/store.py")
    G.add_node("d1", label="Architecture", file_type="document", source_file="docs/arch.md")
    G.add_node("p1", label="LeidenPaper", file_type="paper", source_file="papers/leiden.pdf")
    G.add_node("n1", label="Cache rationale", file_type="note", source_file="wiki-out/ingested/note-1.md")
    G.add_edge("c1", "c2", relation="calls", confidence="EXTRACTED")
    G.add_edge("c1", "d1", relation="mentions", confidence="EXTRACTED")
    G.add_edge("d1", "p1", relation="references", confidence="INFERRED")

    communities = {0: ["c1", "c2", "n1"], 1: ["d1", "p1"]}
    labels = {0: "Storage", 1: "Theory"}
    cohesion = {0: 0.85, 1: 0.42}
    return G, communities, labels, cohesion


def test_index_md_is_written(tmp_path: Path) -> None:
    G, comms, labels, coh = _build_sample_graph()
    to_vault(G, comms, str(tmp_path), community_labels=labels, cohesion=coh)
    assert (tmp_path / "index.md").exists()


def test_index_md_groups_by_file_type(tmp_path: Path) -> None:
    G, comms, labels, coh = _build_sample_graph()
    to_vault(G, comms, str(tmp_path), community_labels=labels, cohesion=coh)
    text = (tmp_path / "index.md").read_text(encoding="utf-8")

    # Each file_type present in graph should produce a heading with count
    assert "## Code (2)" in text
    assert "## Document (1)" in text
    assert "## Paper (1)" in text
    assert "## Note (1)" in text


def test_index_md_includes_wikilinks_for_each_node(tmp_path: Path) -> None:
    G, comms, labels, coh = _build_sample_graph()
    to_vault(G, comms, str(tmp_path), community_labels=labels, cohesion=coh)
    text = (tmp_path / "index.md").read_text(encoding="utf-8")

    for label in ["GraphStore", "indexBy", "Architecture", "LeidenPaper", "Cache rationale"]:
        assert f"[[{label}]]" in text, f"missing wikilink for {label}"


def test_index_md_includes_community_section(tmp_path: Path) -> None:
    G, comms, labels, coh = _build_sample_graph()
    to_vault(G, comms, str(tmp_path), community_labels=labels, cohesion=coh)
    text = (tmp_path / "index.md").read_text(encoding="utf-8")

    assert "## Communities (2)" in text
    assert "[[_COMMUNITY_Storage]]" in text
    assert "[[_COMMUNITY_Theory]]" in text
    # Includes member count and cohesion
    assert "3 members" in text  # Storage has 3
    assert "2 members" in text  # Theory has 2
    assert "0.85" in text
    assert "0.42" in text


def test_index_md_has_summary_header(tmp_path: Path) -> None:
    G, comms, labels, coh = _build_sample_graph()
    to_vault(G, comms, str(tmp_path), community_labels=labels, cohesion=coh)
    text = (tmp_path / "index.md").read_text(encoding="utf-8")

    # YAML frontmatter present
    assert text.startswith("---\n")
    assert "type: vault-index" in text
    # Summary line shows totals
    assert "5 nodes" in text
    assert "2 communities" in text


def test_index_md_handles_empty_graph(tmp_path: Path) -> None:
    G = nx.Graph()
    to_vault(G, {}, str(tmp_path))
    index = tmp_path / "index.md"
    assert index.exists()
    text = index.read_text(encoding="utf-8")
    assert "0 nodes" in text


def test_index_md_handles_node_without_file_type(tmp_path: Path) -> None:
    G = nx.Graph()
    G.add_node("x1", label="Mystery")  # no file_type
    to_vault(G, {0: ["x1"]}, str(tmp_path), community_labels={0: "Misc"})
    text = (tmp_path / "index.md").read_text(encoding="utf-8")
    # Falls back to "Other" bucket
    assert "## Other (1)" in text
    assert "[[Mystery]]" in text
