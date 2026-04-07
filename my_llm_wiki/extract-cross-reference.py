# cross-reference code entities mentioned in docs/papers
# Creates INFERRED edges between code nodes and doc nodes when
# a code entity name (class, function) appears in document text
from __future__ import annotations
import re
from pathlib import Path

import networkx as nx


def _code_entities(G: nx.Graph) -> dict[str, str]:
    """Build lookup: lowercased label → node_id for code nodes worth matching."""
    entities: dict[str, str] = {}
    for nid, data in G.nodes(data=True):
        if data.get("file_type") != "code":
            continue
        label = data.get("label", "")
        # Skip file-hub nodes, method stubs, and very short names
        if not label or len(label) < 3:
            continue
        if label.startswith(".") and label.endswith("()"):
            continue  # method stub
        source = data.get("source_file", "")
        if source and label == Path(source).name:
            continue  # file-level hub
        # Strip trailing () for matching
        clean = label.rstrip("()")
        if len(clean) < 3:
            continue
        entities[clean.lower()] = nid
    return entities


def _doc_nodes_with_text(G: nx.Graph, root: Path) -> list[tuple[str, str, str]]:
    """Return (node_id, source_file, text_content) for document nodes."""
    results = []
    seen_files: set[str] = set()
    for nid, data in G.nodes(data=True):
        if data.get("file_type") not in ("document", "paper"):
            continue
        source = data.get("source_file", "")
        if not source or source in seen_files:
            continue
        seen_files.add(source)
        # Try to read the source file
        path = root / source if not Path(source).is_absolute() else Path(source)
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            results.append((nid, source, text))
        except Exception:
            continue
    return results


def cross_reference(G: nx.Graph, root: Path) -> list[dict]:
    """Find code entities mentioned in docs and create INFERRED edges.

    Returns list of edge dicts to add to the graph.
    """
    code_ents = _code_entities(G)
    if not code_ents:
        return []

    doc_texts = _doc_nodes_with_text(G, root)
    if not doc_texts:
        return []

    # Build regex pattern matching any code entity name (word boundaries)
    # Sort by length descending to match longer names first
    sorted_names = sorted(code_ents.keys(), key=len, reverse=True)
    # Escape regex special chars and require word boundaries
    pattern_parts = [re.escape(name) for name in sorted_names]
    if not pattern_parts:
        return []
    pattern = re.compile(r'\b(' + '|'.join(pattern_parts) + r')\b', re.IGNORECASE)

    edges: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()

    for doc_nid, source_file, text in doc_texts:
        matches = pattern.findall(text)
        for match in matches:
            code_nid = code_ents.get(match.lower())
            if not code_nid:
                continue
            pair = (code_nid, doc_nid)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            edges.append({
                "source": doc_nid,
                "target": code_nid,
                "relation": "mentions",
                "confidence": "INFERRED",
                "source_file": source_file,
            })

    return edges
