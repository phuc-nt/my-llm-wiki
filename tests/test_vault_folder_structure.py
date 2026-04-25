"""Tests for vault folder structure by file_type (A3).

Node notes go into <type>/ subfolders (code/, document/, paper/, image/, note/, other/).
Community notes go into communities/.
index.md and log.md stay at vault root.
Wikilinks remain basename-only — Obsidian resolves them across the vault.
"""
from __future__ import annotations

from pathlib import Path

import networkx as nx

from my_llm_wiki import to_vault


def _build_graph() -> tuple[nx.Graph, dict[int, list[str]], dict[int, str]]:
    G = nx.Graph()
    G.add_node("c1", label="GraphStore", file_type="code", source_file="src/store.py")
    G.add_node("d1", label="Architecture", file_type="document", source_file="docs/arch.md")
    G.add_node("p1", label="LeidenPaper", file_type="paper", source_file="papers/leiden.pdf")
    G.add_node("i1", label="Diagram", file_type="image", source_file="img/diag.png")
    G.add_node("n1", label="CacheRationale", file_type="note", source_file="ingested/n.md")
    G.add_node("x1", label="Mystery")  # no file_type
    G.add_edge("c1", "d1", relation="mentions")
    return G, {0: ["c1", "d1", "p1", "i1", "n1", "x1"]}, {0: "Mixed"}


def test_node_notes_grouped_into_type_subfolders(tmp_path: Path) -> None:
    G, comms, labels = _build_graph()
    to_vault(G, comms, str(tmp_path), community_labels=labels)
    assert (tmp_path / "code" / "GraphStore.md").exists()
    assert (tmp_path / "document" / "Architecture.md").exists()
    assert (tmp_path / "paper" / "LeidenPaper.md").exists()
    assert (tmp_path / "image" / "Diagram.md").exists()
    assert (tmp_path / "note" / "CacheRationale.md").exists()


def test_unknown_type_goes_to_other_folder(tmp_path: Path) -> None:
    G, comms, labels = _build_graph()
    to_vault(G, comms, str(tmp_path), community_labels=labels)
    assert (tmp_path / "other" / "Mystery.md").exists()


def test_communities_in_communities_subfolder(tmp_path: Path) -> None:
    G, comms, labels = _build_graph()
    to_vault(G, comms, str(tmp_path), community_labels=labels)
    assert (tmp_path / "communities" / "_COMMUNITY_Mixed.md").exists()


def test_index_and_log_stay_at_root(tmp_path: Path) -> None:
    G, comms, labels = _build_graph()
    to_vault(G, comms, str(tmp_path), community_labels=labels)
    assert (tmp_path / "index.md").exists()
    assert (tmp_path / "log.md").exists()
    # Not under any subfolder
    assert not (tmp_path / "code" / "index.md").exists()


def test_wikilinks_remain_basename_only(tmp_path: Path) -> None:
    """Obsidian resolves [[Name]] across vault by basename — no path needed."""
    G, comms, labels = _build_graph()
    to_vault(G, comms, str(tmp_path), community_labels=labels)
    # GraphStore mentions Architecture — link should be [[Architecture]] not [[document/Architecture]]
    text = (tmp_path / "code" / "GraphStore.md").read_text(encoding="utf-8")
    assert "[[Architecture]]" in text
    assert "[[document/Architecture]]" not in text


def test_index_uses_basename_links(tmp_path: Path) -> None:
    G, comms, labels = _build_graph()
    to_vault(G, comms, str(tmp_path), community_labels=labels)
    text = (tmp_path / "index.md").read_text(encoding="utf-8")
    # Index lists [[NodeLabel]] not [[code/NodeLabel]]
    assert "[[GraphStore]]" in text
    assert "[[code/GraphStore]]" not in text
    # Communities link too
    assert "[[_COMMUNITY_Mixed]]" in text


def test_no_subfolder_when_no_nodes_of_that_type(tmp_path: Path) -> None:
    G = nx.Graph()
    G.add_node("c1", label="OnlyCode", file_type="code")
    to_vault(G, {0: ["c1"]}, str(tmp_path))
    assert (tmp_path / "code").is_dir()
    assert not (tmp_path / "document").exists()
    assert not (tmp_path / "paper").exists()
