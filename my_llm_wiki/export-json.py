# export graph to JSON (node-link format with community assignments and hyperedges)
from __future__ import annotations
import importlib
import json

import networkx as nx
from networkx.readwrite import json_graph

_analyze = importlib.import_module("my_llm_wiki.analyze-graph")
_node_community_map = _analyze._node_community_map

_CONFIDENCE_SCORE_DEFAULTS: dict[str, float] = {
    "EXTRACTED": 1.0,
    "INFERRED": 0.5,
    "AMBIGUOUS": 0.2,
}


def attach_hyperedges(G: nx.Graph, hyperedges: list) -> None:
    """Merge hyperedges into the graph's metadata dict (deduplicates by id)."""
    existing = G.graph.get("hyperedges", [])
    seen_ids = {h["id"] for h in existing}
    for h in hyperedges:
        if h.get("id") and h["id"] not in seen_ids:
            existing.append(h)
            seen_ids.add(h["id"])
    G.graph["hyperedges"] = existing


def to_json(G: nx.Graph, communities: dict[int, list[str]], output_path: str) -> None:
    """Serialize graph to a node-link JSON file.

    Each node gains a ``community`` field; each edge gains a ``confidence_score``
    if absent. Hyperedges stored in ``G.graph["hyperedges"]`` are included.
    """
    node_community = _node_community_map(communities)
    data = json_graph.node_link_data(G, edges="links")

    for node in data["nodes"]:
        node["community"] = node_community.get(node["id"])

    for link in data["links"]:
        if "confidence_score" not in link:
            conf = link.get("confidence", "EXTRACTED")
            link["confidence_score"] = _CONFIDENCE_SCORE_DEFAULTS.get(conf, 1.0)

    data["hyperedges"] = getattr(G, "graph", {}).get("hyperedges", [])

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
