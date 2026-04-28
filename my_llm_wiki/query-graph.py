# CLI query interface for wiki-out/graph.json
# Supports: node lookup, neighbors, community listing, shortest path, stats, search,
#           orphan detection, stale wikilink ref detection
from __future__ import annotations
import importlib
import json
import re
import sys
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph

_analyze = importlib.import_module("my_llm_wiki.analyze-graph")
_god_nodes = _analyze.god_nodes


def _load_graph(graph_path: str) -> nx.Graph:
    """Load graph from JSON file, returning a NetworkX graph."""
    data = json.loads(Path(graph_path).read_text(encoding="utf-8"))
    return json_graph.node_link_graph(data, edges="links")


def _communities_from_graph(G: nx.Graph) -> dict[int, list[str]]:
    """Reconstruct community dict from community property stored on nodes."""
    communities: dict[int, list[str]] = {}
    for node_id, data in G.nodes(data=True):
        cid = data.get("community")
        if cid is not None:
            communities.setdefault(int(cid), []).append(node_id)
    return communities


def _find_nodes(G: nx.Graph, term: str) -> list[str]:
    """Case-insensitive search by label or node ID. Exact matches ranked first."""
    t = term.lower()
    exact, partial = [], []
    for nid, d in G.nodes(data=True):
        label = d.get("label", "").lower()
        if label == t or nid.lower() == t:
            exact.append(nid)
        elif t in label:
            partial.append(nid)
    return exact + partial


def _score_nodes(G: nx.Graph, terms: list[str]) -> list[tuple[float, str]]:
    """Score nodes by keyword match on label + source_file."""
    scored = []
    for nid, data in G.nodes(data=True):
        label = data.get("label", "").lower()
        source = data.get("source_file", "").lower()
        score = sum(1 for t in terms if t in label) + sum(0.5 for t in terms if t in source)
        if score > 0:
            scored.append((score, nid))
    return sorted(scored, reverse=True)


def cmd_node(G: nx.Graph, label: str) -> str:
    """Show details for a node matching the label."""
    matches = _find_nodes(G, label)
    if not matches:
        return f"No node matching '{label}'."
    lines = []
    for nid in matches[:5]:
        d = G.nodes[nid]
        lines += [
            f"  {d.get('label', nid)}",
            f"    source: {d.get('source_file', '')} {d.get('source_location', '')}",
            f"    type: {d.get('file_type', '')}  community: {d.get('community', '')}  degree: {G.degree(nid)}",
        ]
        if d.get("page") is not None:
            lines.append(f"    Page: {d['page']}")
        if d.get("signature"):
            lines.append(f"    signature: {d['signature']}")
        if d.get("description"):
            lines.append(f"    doc: {d['description']}")
    return "\n".join(lines)


def cmd_neighbors(G: nx.Graph, label: str) -> str:
    """Show direct neighbors of a node."""
    matches = _find_nodes(G, label)
    if not matches:
        return f"No node matching '{label}'."
    nid = matches[0]
    lines = [f"Neighbors of {G.nodes[nid].get('label', nid)}:"]
    for nb in sorted(G.neighbors(nid), key=lambda n: G.nodes[n].get("label", n)):
        ed = G.edges[nid, nb]
        lines.append(f"  -> {G.nodes[nb].get('label', nb)}  [{ed.get('relation', '')}] [{ed.get('confidence', '')}]")
    return "\n".join(lines)


def cmd_community(G: nx.Graph, communities: dict[int, list[str]], cid: int) -> str:
    """List all nodes in a community."""
    members = communities.get(cid)
    if not members:
        return f"Community {cid} not found."
    lines = [f"Community {cid} ({len(members)} nodes):"]
    for nid in sorted(members, key=lambda n: G.degree(n), reverse=True):
        d = G.nodes[nid]
        lines.append(f"  {d.get('label', nid)}  [{d.get('source_file', '')}]  deg={G.degree(nid)}")
    return "\n".join(lines)


def cmd_path(G: nx.Graph, source: str, target: str) -> str:
    """Find shortest path between two concepts."""
    src_matches = _find_nodes(G, source)
    tgt_matches = _find_nodes(G, target)
    if not src_matches:
        return f"No node matching '{source}'."
    if not tgt_matches:
        return f"No node matching '{target}'."
    try:
        path_nodes = nx.shortest_path(G, src_matches[0], tgt_matches[0])
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return f"No path between '{source}' and '{target}'."
    parts = []
    for i in range(len(path_nodes) - 1):
        u, v = path_nodes[i], path_nodes[i + 1]
        ed = G.edges[u, v]
        if i == 0:
            parts.append(G.nodes[u].get("label", u))
        parts.append(f"--{ed.get('relation', '')}--> {G.nodes[v].get('label', v)}")
    return f"Path ({len(path_nodes)-1} hops):\n  " + " ".join(parts)


def cmd_stats(G: nx.Graph, communities: dict[int, list[str]]) -> str:
    """Show graph summary statistics."""
    confs = [d.get("confidence", "EXTRACTED") for _, _, d in G.edges(data=True)]
    total = len(confs) or 1
    return (
        f"Nodes: {G.number_of_nodes()}\n"
        f"Edges: {G.number_of_edges()}\n"
        f"Communities: {len(communities)}\n"
        f"EXTRACTED: {round(confs.count('EXTRACTED')/total*100)}%\n"
        f"INFERRED: {round(confs.count('INFERRED')/total*100)}%\n"
        f"AMBIGUOUS: {round(confs.count('AMBIGUOUS')/total*100)}%"
    )


def cmd_gods(G: nx.Graph) -> str:
    """Show top connected nodes."""
    nodes = _god_nodes(G)
    lines = ["God nodes (most connected):"]
    lines += [f"  {i}. {n['label']} - {n['edges']} edges" for i, n in enumerate(nodes, 1)]
    return "\n".join(lines)


def cmd_search(G: nx.Graph, query: str) -> str:
    """Keyword search across all nodes."""
    terms = [t.lower() for t in query.split() if len(t) > 1]
    if not terms:
        return "Provide search terms."
    scored = _score_nodes(G, terms)
    if not scored:
        return "No matches."
    lines = [f"Search results for '{query}':"]
    for score, nid in scored[:15]:
        d = G.nodes[nid]
        lines.append(f"  [{score:.1f}] {d.get('label', nid)}  [{d.get('source_file', '')}]")
    return "\n".join(lines)


_HUB_FILE_TYPES = {"image"}


def cmd_orphans(G: nx.Graph, include_hubs: bool = False) -> str:
    """List nodes with no edges (degree == 0).

    Args:
        G: The knowledge graph.
        include_hubs: When False (default), skip image-type hub nodes — they
            are intentionally low-degree and would generate false-positive noise.
    """
    orphan_labels: list[str] = []
    for nid, data in G.nodes(data=True):
        if G.degree(nid) != 0:
            continue
        if not include_hubs and data.get("file_type") in _HUB_FILE_TYPES:
            continue
        orphan_labels.append(data.get("label", nid))

    lines: list[str] = []
    for lbl in sorted(orphan_labels):
        lines.append(f"  {lbl}")
    count = len(orphan_labels)
    lines.append(f"\n{count} orphan node(s) found.")
    if not include_hubs:
        lines.append("(image hub nodes excluded — use --include-hubs to show them)")
    return "\n".join(lines)


# Regex for wikilinks: [[Label]] or [[Label#Anchor]]
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_FENCE_RE = re.compile(r"^```")


def cmd_stale_refs(G: nx.Graph, vault_dir: Path) -> str:
    """Scan vault markdown files for [[wikilinks]] that don't resolve to a node.

    Skips content inside fenced code blocks (``` ... ```).
    Normalises [[Label#Anchor]] to just "Label" before lookup.

    Returns one line per stale ref: "<file>:<line> -> [[Missing]]"
    plus a summary count.
    """
    # Build set of known labels for O(1) lookup (case-sensitive match)
    known_labels: set[str] = {
        data.get("label", nid)
        for nid, data in G.nodes(data=True)
    }

    stale: list[str] = []

    for md_file in sorted(vault_dir.rglob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        in_fence = False
        for lineno, raw in enumerate(text.splitlines(), start=1):
            # Toggle fenced code block state
            if _FENCE_RE.match(raw.strip()):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for match in _WIKILINK_RE.finditer(raw):
                ref = match.group(1)
                # Normalise section anchors: "Foo#Bar" → "Foo"
                label = ref.split("#")[0].strip()
                if label and label not in known_labels:
                    rel = md_file.relative_to(vault_dir)
                    stale.append(f"  {rel}:{lineno} -> [[{label}]]")

    count = len(stale)
    lines = stale + [f"\n{count} stale reference(s) found."]
    return "\n".join(lines)


_USAGE = """\
Usage: llm-wiki query <command> [args]

Commands:
  search <terms>          Keyword search across all nodes
  node <label>            Show node details
  neighbors <label>       Show direct connections
  community <id>          List community members
  path <source> <target>  Shortest path between two concepts
  gods                    Most connected nodes
  stats                   Graph summary statistics
  orphans                 List nodes with no connections (isolated concepts)
  stale-refs <vault>      Find [[wikilinks]] that don't resolve to a graph node

Examples:
  llm-wiki query search GraphStore
  llm-wiki query node GraphStore
  llm-wiki query neighbors GraphStore
  llm-wiki query community 0
  llm-wiki query path GraphStore Settings
  llm-wiki query gods
  llm-wiki query stats
  llm-wiki query orphans
  llm-wiki query orphans --include-hubs
  llm-wiki query stale-refs wiki-out/vault
"""


def query_main(args: list[str], graph_path: str = "wiki-out/graph.json") -> None:
    """Entry point for `llm-wiki query` subcommand."""
    if not args:
        print(_USAGE)
        return

    path = Path(graph_path)
    if not path.exists():
        print(f"[wiki] Graph not found: {path}")
        print("[wiki] Run `llm-wiki .` first to build the graph.")
        sys.exit(1)

    G = _load_graph(graph_path)
    communities = _communities_from_graph(G)

    cmd = args[0]
    rest = args[1:]

    if cmd == "search" and rest:
        print(cmd_search(G, " ".join(rest)))
    elif cmd == "node" and rest:
        print(cmd_node(G, " ".join(rest)))
    elif cmd == "neighbors" and rest:
        print(cmd_neighbors(G, " ".join(rest)))
    elif cmd == "community" and rest:
        try:
            print(cmd_community(G, communities, int(rest[0])))
        except ValueError:
            print(f"Community ID must be a number, got '{rest[0]}'")
    elif cmd == "path" and len(rest) >= 2:
        print(cmd_path(G, rest[0], " ".join(rest[1:])))
    elif cmd == "gods":
        print(cmd_gods(G))
    elif cmd == "stats":
        print(cmd_stats(G, communities))
    elif cmd == "orphans":
        include_hubs = "--include-hubs" in rest
        print(cmd_orphans(G, include_hubs=include_hubs))
    elif cmd == "stale-refs":
        # Positional arg: vault directory (default: wiki-out/vault)
        vault_arg = next((r for r in rest if not r.startswith("--")), "wiki-out/vault")
        vault_dir = Path(vault_arg)
        if not vault_dir.is_dir():
            print(f"[wiki] Vault directory not found: {vault_dir}")
            sys.exit(1)
        print(cmd_stale_refs(G, vault_dir))
    else:
        print(_USAGE)
