"""Tests for cmd_orphans in query-graph.py (TDD red→green).

Fixture: 5-node graph — A-B-C connected in chain, D and E isolated.
Hub flag: image-type nodes with degree 0 are excluded by default (include_hubs=False).
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import networkx as nx
import pytest

_query = importlib.import_module("my_llm_wiki.query-graph")
cmd_orphans = _query.cmd_orphans


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_graph() -> nx.Graph:
    """5-node graph: A-B-C connected, D and E isolated."""
    G = nx.Graph()
    # Connected cluster
    G.add_node("A", label="Alpha", file_type="code", community=0)
    G.add_node("B", label="Beta", file_type="code", community=0)
    G.add_node("C", label="Gamma", file_type="code", community=0)
    G.add_edge("A", "B", relation="calls", confidence="EXTRACTED")
    G.add_edge("B", "C", relation="calls", confidence="EXTRACTED")
    # Isolated nodes
    G.add_node("D", label="Delta", file_type="code", community=1)
    G.add_node("E", label="Epsilon", file_type="document", community=2)
    return G


def _make_graph_with_image_hub() -> nx.Graph:
    """Same as _make_graph but adds an isolated image hub node."""
    G = _make_graph()
    G.add_node("IMG", label="diagram.png", file_type="image", community=3)
    return G


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_orphans_returns_isolated_nodes() -> None:
    """cmd_orphans should return both isolated nodes (D and E)."""
    G = _make_graph()
    result = cmd_orphans(G)
    assert "Delta" in result
    assert "Epsilon" in result


def test_orphans_excludes_connected_nodes() -> None:
    """Connected nodes (Alpha, Beta, Gamma) must NOT appear in orphan output."""
    G = _make_graph()
    result = cmd_orphans(G)
    assert "Alpha" not in result
    assert "Beta" not in result
    assert "Gamma" not in result


def test_orphans_summary_count() -> None:
    """Output must include a summary line with the count of orphans found."""
    G = _make_graph()
    result = cmd_orphans(G)
    # The summary line should mention '2' orphans
    assert "2" in result


def test_orphans_empty_graph() -> None:
    """No nodes → 0 orphans, no error."""
    G = nx.Graph()
    result = cmd_orphans(G)
    assert "0" in result


def test_orphans_excludes_image_hubs_by_default() -> None:
    """Image-type isolated nodes are excluded when include_hubs=False (default)."""
    G = _make_graph_with_image_hub()
    result = cmd_orphans(G, include_hubs=False)
    assert "diagram.png" not in result
    # Other isolated nodes still present
    assert "Delta" in result
    assert "Epsilon" in result


def test_orphans_includes_image_hubs_when_flag_set() -> None:
    """Image-type isolated nodes appear when include_hubs=True."""
    G = _make_graph_with_image_hub()
    result = cmd_orphans(G, include_hubs=True)
    assert "diagram.png" in result


def test_orphans_no_isolated_nodes() -> None:
    """Fully connected graph → 0 orphans."""
    G = nx.Graph()
    G.add_node("X", label="X", file_type="code")
    G.add_node("Y", label="Y", file_type="code")
    G.add_edge("X", "Y", relation="calls")
    result = cmd_orphans(G)
    assert "0" in result
