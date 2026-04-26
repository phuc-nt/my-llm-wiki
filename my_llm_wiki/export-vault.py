# export graph as a markdown vault: one .md per node, one _COMMUNITY_.md per community,
# .vault/graph.json for community coloring in graph view
from __future__ import annotations
import importlib
import json
import re
from collections import Counter
from pathlib import Path

import networkx as nx

from my_llm_wiki.constants import COMMUNITY_COLORS

_vault_log = importlib.import_module("my_llm_wiki.vault-log")
append_log_entry = _vault_log.append_log_entry

_analyze = importlib.import_module("my_llm_wiki.analyze-graph")
_node_community_map = _analyze._node_community_map
_dominant_confidence = _analyze._dominant_confidence

# Map file_type → wiki tag
_FTYPE_TAG: dict[str, str] = {
    "code": "wiki/code",
    "document": "wiki/document",
    "paper": "wiki/paper",
    "image": "wiki/image",
}


def _safe_name(label: str) -> str:
    """Strip characters forbidden in vault filenames. Prevents path traversal."""
    name = re.sub(r'[\\/*?:"<>|#^[\]]', "", label).strip()
    name = name.replace("..", "")  # prevent path traversal
    return name or "unnamed"


def _truncate_label(label: str) -> str:
    """Truncate long labels for use as vault filenames.

    If the label contains more than 8 words, truncate to 60 chars and append ellipsis.
    Strips trailing spaces/punctuation before the ellipsis.
    """
    words = label.split()
    if len(words) <= 8:
        return label
    truncated = label[:60].rstrip(" ,;:-.")
    return truncated + "\u2026"


def _dedup_key(name: str) -> str:
    """Normalize filename for dedup: strip trailing ellipsis/punctuation."""
    return name.rstrip("\u2026. ")


def _build_node_filenames(G: nx.Graph) -> dict[str, str]:
    """Map node_id → deduplicated safe filename (without .md extension)."""
    node_filename: dict[str, str] = {}
    seen_names: dict[str, int] = {}
    for node_id, data in G.nodes(data=True):
        raw_label = data.get("label", node_id)
        base = _safe_name(_truncate_label(raw_label))
        key = _dedup_key(base)
        if key in seen_names:
            seen_names[key] += 1
            node_filename[node_id] = f"{base}_{seen_names[key]}"
        else:
            seen_names[key] = 0
            node_filename[node_id] = base
    return node_filename


def _node_subfolder(file_type: str | None) -> str:
    """Map a node's file_type to its vault subfolder. Unknown → 'other'."""
    return file_type if file_type else "other"


def _write_node_notes(
    G: nx.Graph,
    out: Path,
    node_filename: dict[str, str],
    node_community: dict[str, int],
    community_labels: dict[int, str] | None,
) -> None:
    """Write one .md file per node with YAML frontmatter and [[wikilinks]].

    Files are grouped into <out>/<file_type>/ subfolders. Wikilinks stay
    basename-only — Obsidian resolves them across the vault regardless of folder.
    """
    for node_id, data in G.nodes(data=True):
        label = data.get("label", node_id)
        cid = node_community.get(node_id)
        community_name = (
            community_labels.get(cid, f"Community {cid}")
            if community_labels and cid is not None
            else f"Community {cid}"
        )

        ftype = data.get("file_type", "")
        ftype_tag = _FTYPE_TAG.get(ftype, f"wiki/{ftype}" if ftype else "wiki/document")
        dom_conf = _dominant_confidence(G, node_id)
        conf_tag = f"wiki/{dom_conf}"
        comm_tag = f"community/{community_name.replace(' ', '_')}"
        node_tags = [ftype_tag, conf_tag, comm_tag]

        lines: list[str] = [
            "---",
            f'source_file: "{data.get("source_file", "")}"',
            f'type: "{ftype}"',
            f'community: "{community_name}"',
        ]
        if data.get("source_location"):
            lines.append(f'location: "{data["source_location"]}"')
        if data.get("pages"):
            lines.append(f'pages: {data["pages"]}')
        lines.append("tags:")
        for tag in node_tags:
            lines.append(f"  - {tag}")
        lines += ["---", "", f"# {label}", ""]

        neighbors = list(G.neighbors(node_id))
        if neighbors:
            lines.append("## Connections")
            for neighbor in sorted(neighbors, key=lambda n: G.nodes[n].get("label", n)):
                edge_data = G.edges[node_id, neighbor]
                neighbor_label = node_filename[neighbor]
                relation = edge_data.get("relation", "")
                confidence = edge_data.get("confidence", "EXTRACTED")
                lines.append(f"- [[{neighbor_label}]] - `{relation}` [{confidence}]")
            lines.append("")

        # Inline tags for tag panel
        inline_tags = " ".join(f"#{t}" for t in node_tags)
        lines.append(inline_tags)

        subdir = out / _node_subfolder(ftype)
        subdir.mkdir(parents=True, exist_ok=True)
        (subdir / (node_filename[node_id] + ".md")).write_text("\n".join(lines), encoding="utf-8")


def _write_community_notes(
    G: nx.Graph,
    out: Path,
    communities: dict[int, list[str]],
    node_filename: dict[str, str],
    node_community: dict[str, int],
    community_labels: dict[int, str] | None,
    cohesion: dict[int, float] | None,
) -> int:
    """Write one _COMMUNITY_<name>.md overview note per community. Returns count written."""
    # Precompute inter-community edge counts
    inter: dict[int, dict[int, int]] = {cid: {} for cid in communities}
    for u, v in G.edges():
        cu = node_community.get(u)
        cv = node_community.get(v)
        if cu is not None and cv is not None and cu != cv:
            inter.setdefault(cu, {})
            inter.setdefault(cv, {})
            inter[cu][cv] = inter[cu].get(cv, 0) + 1
            inter[cv][cu] = inter[cv].get(cu, 0) + 1

    def _community_reach(node_id: str) -> int:
        return len({
            node_community[nb]
            for nb in G.neighbors(node_id)
            if nb in node_community and node_community[nb] != node_community.get(node_id)
        })

    written = 0
    for cid, members in communities.items():
        community_name = (
            community_labels.get(cid, f"Community {cid}")
            if community_labels and cid is not None
            else f"Community {cid}"
        )
        coh_value = cohesion.get(cid) if cohesion else None

        lines: list[str] = [
            "---",
            "type: community",
        ]
        if coh_value is not None:
            lines.append(f"cohesion: {coh_value:.2f}")
        lines += [f"members: {len(members)}", "---", "", f"# {community_name}", ""]

        if coh_value is not None:
            cohesion_desc = (
                "tightly connected" if coh_value >= 0.7
                else "moderately connected" if coh_value >= 0.4
                else "loosely connected"
            )
            lines.append(f"**Cohesion:** {coh_value:.2f} - {cohesion_desc}")
        lines += [f"**Members:** {len(members)} nodes", "", "## Members"]

        for node_id in sorted(members, key=lambda n: G.nodes[n].get("label", n)):
            data = G.nodes[node_id]
            entry = f"- [[{node_filename[node_id]}]]"
            ftype = data.get("file_type", "")
            source = data.get("source_file", "")
            if ftype:
                entry += f" - {ftype}"
            if source:
                entry += f" - {source}"
            lines.append(entry)
        lines.append("")

        # Dataview live query
        comm_tag_name = community_name.replace(" ", "_")
        lines += [
            "## Live Query",
            "",
            "```dataview",
            f"TABLE source_file, type FROM #community/{comm_tag_name}",
            "SORT file.name ASC",
            "```",
            "",
        ]

        cross = inter.get(cid, {})
        if cross:
            lines.append("## Connections to other communities")
            for other_cid, edge_count in sorted(cross.items(), key=lambda x: -x[1]):
                other_name = (
                    community_labels.get(other_cid, f"Community {other_cid}")
                    if community_labels and other_cid is not None
                    else f"Community {other_cid}"
                )
                other_safe = _safe_name(other_name)
                lines.append(
                    f"- {edge_count} edge{'s' if edge_count != 1 else ''} to [[_COMMUNITY_{other_safe}]]"
                )
            lines.append("")

        bridge_nodes = [
            (node_id, G.degree(node_id), _community_reach(node_id))
            for node_id in members
            if _community_reach(node_id) > 0
        ]
        bridge_nodes.sort(key=lambda x: (-x[2], -x[1]))
        if bridge_nodes[:5]:
            lines.append("## Top bridge nodes")
            for node_id, degree, reach in bridge_nodes[:5]:
                lines.append(
                    f"- [[{node_filename[node_id]}]] - degree {degree}, connects to {reach} "
                    f"{'community' if reach == 1 else 'communities'}"
                )

        community_safe = _safe_name(community_name)
        comm_dir = out / "communities"
        comm_dir.mkdir(parents=True, exist_ok=True)
        (comm_dir / f"_COMMUNITY_{community_safe}.md").write_text("\n".join(lines), encoding="utf-8")
        written += 1

    return written


def _write_index_md(
    G: nx.Graph,
    out: Path,
    node_filename: dict[str, str],
    communities: dict[int, list[str]],
    community_labels: dict[int, str] | None,
    cohesion: dict[int, float] | None,
) -> None:
    """Write vault/index.md — content catalog grouped by file_type + Communities section.

    LLMs read this first to navigate the vault efficiently (Karpathy compounding-artifact pattern).
    """
    # Group nodes by file_type (fall back to "Other" when missing)
    by_type: dict[str, list[str]] = {}
    for node_id, data in G.nodes(data=True):
        ftype = data.get("file_type") or "other"
        by_type.setdefault(ftype, []).append(node_id)

    lines: list[str] = [
        "---",
        "type: vault-index",
        f"nodes: {G.number_of_nodes()}",
        f"communities: {len(communities)}",
        "---",
        "",
        "# Vault Index",
        "",
        f"{G.number_of_nodes()} nodes across {len(communities)} communities.",
        "",
    ]

    # One section per file_type, sorted by section size desc then name
    for ftype in sorted(by_type, key=lambda t: (-len(by_type[t]), t)):
        nodes = by_type[ftype]
        lines.append(f"## {ftype.capitalize()} ({len(nodes)})")
        lines.append("")
        for node_id in sorted(nodes, key=lambda n: G.nodes[n].get("label", n).lower()):
            data = G.nodes[node_id]
            link = node_filename[node_id]
            degree = G.degree(node_id)
            source = data.get("source_file", "")
            entry = f"- [[{link}]] — degree {degree}"
            if source:
                entry += f" · `{source}`"
            lines.append(entry)
        lines.append("")

    # Communities section
    if communities:
        lines.append(f"## Communities ({len(communities)})")
        lines.append("")
        for cid in sorted(communities):
            members = communities[cid]
            name = (community_labels or {}).get(cid, f"Community {cid}")
            safe = _safe_name(name)
            entry = f"- [[_COMMUNITY_{safe}]] — {len(members)} members"
            if cohesion and cid in cohesion:
                entry += f" · cohesion {cohesion[cid]:.2f}"
            lines.append(entry)
        lines.append("")

    (out / "index.md").write_text("\n".join(lines), encoding="utf-8")


def to_vault(
    G: nx.Graph,
    communities: dict[int, list[str]],
    output_dir: str,
    community_labels: dict[int, str] | None = None,
    cohesion: dict[int, float] | None = None,
) -> int:
    """Export graph as a markdown vault.

    Writes:
      - One <NodeLabel>.md per node with YAML frontmatter, [[wikilinks]], inline tags
      - One _COMMUNITY_<name>.md per community with members, dataview query, bridge nodes
      - .vault/graph.json for community coloring in graph view

    Returns total number of notes written (node notes + community notes).
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    node_community = _node_community_map(communities)
    node_filename = _build_node_filenames(G)

    _write_node_notes(G, out, node_filename, node_community, community_labels)

    community_notes = _write_community_notes(
        G, out, communities, node_filename, node_community, community_labels, cohesion
    )

    _write_index_md(G, out, node_filename, communities, community_labels, cohesion)

    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    n_comm = len(communities)
    desc = (
        f"{n_nodes} nodes · {n_edges} edge{'s' if n_edges != 1 else ''} · "
        f"{n_comm} communit{'ies' if n_comm != 1 else 'y'}"
    )
    append_log_entry(out, "build", desc)

    # Write .vault/graph.json to color nodes by community in graph view
    vault_dir = out / ".vault"
    vault_dir.mkdir(exist_ok=True)
    graph_config = {
        "colorGroups": [
            {
                "query": f"tag:#community/{label.replace(' ', '_')}",
                "color": {
                    "a": 1,
                    "rgb": int(COMMUNITY_COLORS[cid % len(COMMUNITY_COLORS)].lstrip("#"), 16),
                },
            }
            for cid, label in sorted((community_labels or {}).items())
        ]
    }
    (vault_dir / "graph.json").write_text(json.dumps(graph_config, indent=2), encoding="utf-8")

    return G.number_of_nodes() + community_notes
