# export graph to interactive vis.js HTML visualization
from __future__ import annotations
import importlib
import json
from pathlib import Path

import networkx as nx

from my_llm_wiki.constants import COMMUNITY_COLORS, MAX_NODES_FOR_VIZ

_sec = importlib.import_module("my_llm_wiki.security-helpers")
sanitize_label = _sec.sanitize_label

_analyze = importlib.import_module("my_llm_wiki.analyze-graph")
_node_community_map = _analyze._node_community_map

_tmpl = importlib.import_module("my_llm_wiki.export-html-templates")
_html_styles = _tmpl.html_styles
_hyperedge_script = _tmpl.hyperedge_script
_html_script = _tmpl.html_script


def to_html(
    G: nx.Graph,
    communities: dict[int, list[str]],
    output_path: str,
    community_labels: dict[int, str] | None = None,
) -> None:
    """Generate an interactive vis.js HTML visualization of the knowledge graph.

    Features: node size by degree, click-to-inspect panel, search box,
    community filter/legend, physics clustering, confidence-styled edges.

    Raises ValueError if graph exceeds MAX_NODES_FOR_VIZ.
    """
    if G.number_of_nodes() > MAX_NODES_FOR_VIZ:
        raise ValueError(
            f"Graph has {G.number_of_nodes()} nodes — too large for HTML viz. "
            f"Use --no-viz or reduce input size (limit: {MAX_NODES_FOR_VIZ})."
        )

    node_community = _node_community_map(communities)
    degree = dict(G.degree())
    max_deg = max(degree.values()) if degree else 1
    max_deg = max(max_deg, 1)  # avoid division by zero

    # Build vis.js nodes list
    vis_nodes = []
    for node_id, data in G.nodes(data=True):
        cid = node_community.get(node_id, 0)
        color = COMMUNITY_COLORS[cid % len(COMMUNITY_COLORS)]
        label = sanitize_label(data.get("label", node_id))
        deg = degree.get(node_id, 1)
        size = 10 + 30 * (deg / max_deg)
        # Only render label text for high-degree nodes by default; others show on hover
        font_size = 12 if deg >= max_deg * 0.15 else 0
        vis_nodes.append({
            "id": node_id,
            "label": label,
            "color": {
                "background": color,
                "border": color,
                "highlight": {"background": "#ffffff", "border": color},
            },
            "size": round(size, 1),
            "font": {"size": font_size, "color": "#ffffff"},
            "title": label,
            "community": cid,
            "community_name": sanitize_label(
                (community_labels or {}).get(cid, f"Community {cid}")
            ),
            "source_file": sanitize_label(data.get("source_file", "")),
            "file_type": data.get("file_type", ""),
            "degree": deg,
        })

    # Build vis.js edges list
    vis_edges = []
    for u, v, data in G.edges(data=True):
        confidence = data.get("confidence", "EXTRACTED")
        relation = data.get("relation", "")
        vis_edges.append({
            "from": u,
            "to": v,
            "label": relation,
            "title": f"{relation} [{confidence}]",
            "dashes": confidence != "EXTRACTED",
            "width": 2 if confidence == "EXTRACTED" else 1,
            "color": {"opacity": 0.7 if confidence == "EXTRACTED" else 0.35},
            "confidence": confidence,
        })

    # Build community legend
    legend_data = []
    for cid in sorted((community_labels or {}).keys()):
        color = COMMUNITY_COLORS[cid % len(COMMUNITY_COLORS)]
        lbl = (community_labels or {}).get(cid, f"Community {cid}")
        n = len(communities.get(cid, []))
        legend_data.append({"cid": cid, "color": color, "label": lbl, "count": n})

    nodes_json = json.dumps(vis_nodes)
    edges_json = json.dumps(vis_edges)
    legend_json = json.dumps(legend_data)
    hyperedges_json = json.dumps(getattr(G, "graph", {}).get("hyperedges", []))
    title = sanitize_label(str(output_path))
    stats = (
        f"{G.number_of_nodes()} nodes &middot; "
        f"{G.number_of_edges()} edges &middot; "
        f"{len(communities)} communities"
    )

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Knowledge Wiki - {title}</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
{_html_styles()}
</head>
<body>
<div id="graph"></div>
<div id="sidebar">
  <div id="search-wrap">
    <input id="search" type="text" placeholder="Search nodes..." autocomplete="off">
    <div id="search-results"></div>
  </div>
  <div id="info-panel">
    <h3>Node Info</h3>
    <div id="info-content"><span class="empty">Click a node to inspect it</span></div>
  </div>
  <div id="legend-wrap">
    <h3>Communities</h3>
    <div id="legend"></div>
  </div>
  <div id="stats">{stats}</div>
</div>
{_html_script(nodes_json, edges_json, legend_json)}
{_hyperedge_script(hyperedges_json)}
</body>
</html>"""

    Path(output_path).write_text(page, encoding="utf-8")
