# Generate semantic community labels from graph topology.
# No LLM calls — purely deterministic heuristics based on node degrees and labels.
from __future__ import annotations

import re
import networkx as nx


def _clean_label(raw: str) -> str:
    """Strip parens/brackets and trailing whitespace from a node label."""
    # Remove trailing () or (args...) patterns
    cleaned = re.sub(r"\(.*?\)", "", raw).strip()
    # Remove trailing punctuation
    cleaned = cleaned.rstrip(".:,;")
    return cleaned.strip()


def _is_short_identifier(label: str) -> bool:
    """Return True if label looks like a code identifier (not a sentence)."""
    words = label.split()
    return len(words) <= 5


def _is_test_file(filename: str) -> bool:
    """Return True if the filename matches test file patterns."""
    name = filename.lower()
    return name.startswith("test_") or name.endswith("_test.py") or "/test" in name or "\\test" in name


def _candidate_label(node_id: str, attrs: dict) -> str | None:
    """Extract a usable short label from node attributes."""
    # Prefer the `label` attribute; fall back to node id
    raw = attrs.get("label", "") or node_id
    # Skip nodes from non-code files unless no choice
    if attrs.get("file_type", "code") != "code":
        return None
    cleaned = _clean_label(raw)
    if not cleaned:
        return None
    if not _is_short_identifier(cleaned):
        return None
    return cleaned


def _deduplicate_labels(labels: list[str]) -> list[str]:
    """Remove labels that share the same stem (case-insensitive prefix of 6+ chars)."""
    seen_stems: set[str] = set()
    result: list[str] = []
    for lbl in labels:
        stem = lbl.lower()[:6]
        if stem not in seen_stems:
            seen_stems.add(stem)
            result.append(lbl)
    return result


def label_communities(G: nx.Graph, communities: dict[int, list[str]]) -> dict[int, str]:
    """Generate semantic labels for each community.

    Args:
        G: NetworkX graph with node attributes including `label` and `file_type`.
        communities: Mapping of community_id -> list of node IDs.

    Returns:
        Mapping of community_id -> human-readable label string (max 40 chars).
    """
    result: dict[int, str] = {}

    for cid, node_ids in communities.items():
        if not node_ids:
            result[cid] = f"Community {cid}"
            continue

        # Determine if this community is dominated by test files
        test_count = 0
        for nid in node_ids:
            attrs = G.nodes.get(nid, {})
            src = attrs.get("source_file", "") or attrs.get("file", "") or nid
            if _is_test_file(str(src)):
                test_count += 1
        is_test_community = test_count > len(node_ids) / 2

        # Rank nodes by degree (high-degree nodes are most central)
        degree_map = dict(G.degree(node_ids))
        ranked = sorted(node_ids, key=lambda n: degree_map.get(n, 0), reverse=True)

        # Collect up to 3 candidate labels from top-ranked nodes
        candidates: list[str] = []
        for nid in ranked:
            if len(candidates) >= 3:
                break
            attrs = G.nodes.get(nid, {})
            lbl = _candidate_label(nid, attrs)
            if lbl:
                candidates.append(lbl)

        # If no code candidates, fall back to any node label regardless of file_type
        if not candidates:
            for nid in ranked[:3]:
                attrs = G.nodes.get(nid, {})
                raw = attrs.get("label", "") or nid
                cleaned = _clean_label(raw)
                if cleaned and _is_short_identifier(cleaned):
                    candidates.append(cleaned)
                    if len(candidates) >= 3:
                        break

        # Still nothing? Use generic fallback
        if not candidates:
            result[cid] = f"Community {cid}"
            continue

        candidates = _deduplicate_labels(candidates)

        # Build combined label from top 2-3 candidates
        combined = " & ".join(candidates[:2])
        if is_test_community:
            combined = f"Test: {combined}"

        # Truncate to 40 chars cleanly (avoid mid-word cut)
        if len(combined) > 40:
            combined = combined[:37].rsplit(" ", 1)[0] + "..."

        result[cid] = combined

    return result
