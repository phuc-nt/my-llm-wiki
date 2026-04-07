# graph analysis helpers — god nodes, surprising connections, community utilities
# shared across report-markdown, export-json, export-html, export-wiki, export-obsidian
from __future__ import annotations
from collections import Counter
from pathlib import Path

import networkx as nx

_CODE_EXTENSIONS = {"py", "ts", "tsx", "js", "go", "rs", "java", "rb", "cpp", "c", "h", "cs", "kt", "scala", "php"}
_PAPER_EXTENSIONS = {"pdf"}
_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "svg"}


def _node_community_map(communities: dict[int, list[str]]) -> dict[str, int]:
    """Invert communities dict: node_id -> community_id."""
    return {n: cid for cid, nodes in communities.items() for n in nodes}


def _is_file_node(G: nx.Graph, node_id: str) -> bool:
    """True if node is a synthetic file-level hub or AST method stub (excluded from analysis)."""
    attrs = G.nodes[node_id]
    label = attrs.get("label", "")
    if not label:
        return False
    source_file = attrs.get("source_file", "")
    if source_file:
        if label == Path(source_file).name:
            return True
    # Method stub: AST extractor labels methods as '.method_name()'
    if label.startswith(".") and label.endswith("()"):
        return True
    # Module-level function stub with no connections
    if label.endswith("()") and G.degree(node_id) <= 1:
        return True
    return False


def _is_concept_node(G: nx.Graph, node_id: str) -> bool:
    """True if node is a manually-injected semantic concept (empty source_file or no extension)."""
    attrs = G.nodes[node_id]
    source_file = attrs.get("source_file", "")
    if not source_file:
        return True
    # Real files have extensions; concept injections often don't
    if not Path(source_file).suffix:
        return True
    return False


def _file_category(path: str) -> str:
    """Classify a file path into a broad category: code, paper, image, or doc."""
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    if ext in _CODE_EXTENSIONS:
        return "code"
    if ext in _PAPER_EXTENSIONS:
        return "paper"
    if ext in _IMAGE_EXTENSIONS:
        return "image"
    return "doc"


def _top_level_dir(path: str) -> str:
    """Return the first path component — used to detect cross-repo edges."""
    return path.split("/")[0] if "/" in path else path


def _surprise_score(G: nx.Graph, u: str, v: str, data: dict,
                    node_community: dict[str, int], u_source: str, v_source: str,
                    ) -> tuple[int, list[str]]:
    """Score how surprising a cross-file edge is (confidence, type, repo, community, hub)."""
    score, reasons = 0, []
    conf = data.get("confidence", "EXTRACTED")
    score += {"AMBIGUOUS": 3, "INFERRED": 2, "EXTRACTED": 1}.get(conf, 1)
    if conf in ("AMBIGUOUS", "INFERRED"):
        reasons.append(f"{conf.lower()} connection - not explicitly stated in source")
    cat_u, cat_v = _file_category(u_source), _file_category(v_source)
    if cat_u != cat_v:
        score += 2
        reasons.append(f"crosses file types ({cat_u} ↔ {cat_v})")
    if _top_level_dir(u_source) != _top_level_dir(v_source):
        score += 2
        reasons.append("connects across different repos/directories")
    cid_u, cid_v = node_community.get(u), node_community.get(v)
    if cid_u is not None and cid_v is not None and cid_u != cid_v:
        score += 1
        reasons.append("bridges separate communities")
    if data.get("relation") == "semantically_similar_to":
        score = int(score * 1.5)
        reasons.append("semantically similar concepts with no structural link")
    deg_u, deg_v = G.degree(u), G.degree(v)
    if min(deg_u, deg_v) <= 2 and max(deg_u, deg_v) >= 5:
        score += 1
        peripheral = G.nodes[u].get("label", u) if deg_u <= 2 else G.nodes[v].get("label", v)
        hub = G.nodes[v].get("label", v) if deg_u <= 2 else G.nodes[u].get("label", u)
        reasons.append(f"peripheral node `{peripheral}` unexpectedly reaches hub `{hub}`")
    return score, reasons


def god_nodes(G: nx.Graph, top_n: int = 10) -> list[dict]:
    """Return top_n most-connected real entities (file-level hubs excluded)."""
    result = []
    for node_id, deg in sorted(dict(G.degree()).items(), key=lambda x: x[1], reverse=True):
        if _is_file_node(G, node_id) or _is_concept_node(G, node_id):
            continue
        result.append({"id": node_id, "label": G.nodes[node_id].get("label", node_id), "edges": deg})
        if len(result) >= top_n:
            break
    return result


def surprising_connections(
    G: nx.Graph,
    communities: dict[int, list[str]] | None = None,
    top_n: int = 5,
) -> list[dict]:
    """Find genuinely surprising connections. Multi-file: cross-file ranked by surprise score. Single-source: cross-community bridges."""
    source_files = {d.get("source_file", "") for _, d in G.nodes(data=True) if d.get("source_file", "")}
    if len(source_files) > 1:
        return _cross_file_surprises(G, communities or {}, top_n)
    return _cross_community_surprises(G, communities or {}, top_n)


def _cross_file_surprises(G: nx.Graph, communities: dict[int, list[str]], top_n: int) -> list[dict]:  # noqa: E501
    """Cross-file edges ranked by surprise score (confidence, type, repo, community, hub)."""
    node_community = _node_community_map(communities)
    candidates = []

    for u, v, data in G.edges(data=True):
        relation = data.get("relation", "")
        if relation in ("imports", "imports_from", "contains", "method"):
            continue
        if _is_concept_node(G, u) or _is_concept_node(G, v):
            continue
        if _is_file_node(G, u) or _is_file_node(G, v):
            continue
        u_source = G.nodes[u].get("source_file", "")
        v_source = G.nodes[v].get("source_file", "")
        if not u_source or not v_source or u_source == v_source:
            continue
        score, reasons = _surprise_score(G, u, v, data, node_community, u_source, v_source)
        src_id, tgt_id = data.get("_src", u), data.get("_tgt", v)
        candidates.append({
            "_score": score,
            "source": G.nodes[src_id].get("label", src_id),
            "target": G.nodes[tgt_id].get("label", tgt_id),
            "source_files": [G.nodes[src_id].get("source_file", ""), G.nodes[tgt_id].get("source_file", "")],
            "confidence": data.get("confidence", "EXTRACTED"),
            "relation": relation,
            "why": "; ".join(reasons) if reasons else "cross-file semantic connection",
        })

    candidates.sort(key=lambda x: x["_score"], reverse=True)
    for c in candidates:
        c.pop("_score")
    if candidates:
        return candidates[:top_n]
    return _cross_community_surprises(G, communities, top_n)


def _cross_community_surprises(G: nx.Graph, communities: dict[int, list[str]], top_n: int) -> list[dict]:
    """Single-source: find edges bridging different communities. Falls back to edge betweenness centrality."""
    if not communities:
        if G.number_of_edges() == 0:
            return []
        betweenness = nx.edge_betweenness_centrality(G)
        result = []
        for (u, v), score in sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:top_n]:
            data = G.edges[u, v]
            result.append({
                "source": G.nodes[u].get("label", u),
                "target": G.nodes[v].get("label", v),
                "source_files": [G.nodes[u].get("source_file", ""), G.nodes[v].get("source_file", "")],
                "confidence": data.get("confidence", "EXTRACTED"),
                "relation": data.get("relation", ""),
                "note": f"Bridges graph structure (betweenness={score:.3f})",
            })
        return result

    node_community = _node_community_map(communities)
    surprises = []
    for u, v, data in G.edges(data=True):
        cid_u, cid_v = node_community.get(u), node_community.get(v)
        if cid_u is None or cid_v is None or cid_u == cid_v:
            continue
        if _is_file_node(G, u) or _is_file_node(G, v):
            continue
        relation = data.get("relation", "")
        if relation in ("imports", "imports_from", "contains", "method"):
            continue
        src_id, tgt_id = data.get("_src", u), data.get("_tgt", v)
        surprises.append({
            "source": G.nodes[src_id].get("label", src_id),
            "target": G.nodes[tgt_id].get("label", tgt_id),
            "source_files": [G.nodes[src_id].get("source_file", ""), G.nodes[tgt_id].get("source_file", "")],
            "confidence": data.get("confidence", "EXTRACTED"),
            "relation": relation,
            "note": f"Bridges community {cid_u} → community {cid_v}",
            "_pair": tuple(sorted([cid_u, cid_v])),
        })

    order = {"AMBIGUOUS": 0, "INFERRED": 1, "EXTRACTED": 2}
    surprises.sort(key=lambda x: order.get(x["confidence"], 3))
    # Deduplicate by community pair — one representative edge per (A→B) boundary
    seen_pairs: set[tuple] = set()
    deduped = []
    for s in surprises:
        pair = s.pop("_pair")
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            deduped.append(s)
    return deduped[:top_n]


def _dominant_confidence(G: nx.Graph, node_id: str) -> str:
    """Return the most common confidence value across all edges for a node."""
    confs = [edata.get("confidence", "EXTRACTED") for _, _, edata in G.edges(node_id, data=True)]
    if not confs:
        return "EXTRACTED"
    return Counter(confs).most_common(1)[0][0]
