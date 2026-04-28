# capture-filters.py — filter pipeline, secret detection, and suggestion helpers for llm-wiki capture
# Split from capture.py per KISS/200-LOC rule.
from __future__ import annotations

import importlib
import json
import re
from pathlib import Path
from typing import Iterator

_secret_scan = importlib.import_module("my_llm_wiki.secret-patterns")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_LENGTH = 50  # minimum user message length in chars

# Decision/rationale keyword pattern (case-insensitive, broad word boundary)
KEYWORD_RE = re.compile(
    r"\b(vì|lý do|because|rationale|trade-off|tradeoff|decided|design choice)\b",
    re.IGNORECASE,
)

# Catch-all for long base64-ish blobs that escape the structured patterns.
# Conservative: any 40+ char run of base64 alphabet is suspicious.
_BASE64_BLOB_RE = re.compile(r"[A-Za-z0-9+/=]{40,}")

# Tag heuristics: compiled pattern → tag name
_TAG_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(decided|decision|design choice)\b", re.IGNORECASE), "decision"),
    (re.compile(r"\b(rationale|lý do|vì)\b", re.IGNORECASE), "rationale"),
    (re.compile(r"\b(trade-off|tradeoff)\b", re.IGNORECASE), "tradeoff"),
    (re.compile(r"\bbecause\b", re.IGNORECASE), "rationale"),
]

# [[WikiLink]] extractor
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


# ---------------------------------------------------------------------------
# Secret detection
# ---------------------------------------------------------------------------

def has_secret(text: str) -> bool:
    """Return True if text contains any known secret pattern.

    Delegates to the shared secret-patterns module so capture stays in lock-step
    with note-writer's coverage. Adds a base64-blob catch-all for long opaque
    strings that don't match a labelled pattern.
    """
    if _secret_scan.has_secret(text):
        return True
    return bool(_BASE64_BLOB_RE.search(text))


# ---------------------------------------------------------------------------
# Content extractor — handle multi-block Claude schema
# ---------------------------------------------------------------------------

def _extract_content(raw_content: object) -> str | None:
    """Normalise content field: str passthrough, list-of-blocks → join text parts."""
    if isinstance(raw_content, str):
        return raw_content
    if isinstance(raw_content, list):
        parts = [
            block.get("text", "")
            for block in raw_content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return " ".join(parts)
    return None


# ---------------------------------------------------------------------------
# Filter pipeline
# ---------------------------------------------------------------------------

def iter_candidates(session_path: Path) -> Iterator[dict]:
    """Yield candidate dicts from a single session jsonl file.

    Filters (all must pass):
      - role == "user"
      - len(content) >= MIN_LENGTH
      - no secret pattern matched
      - at least one decision/rationale keyword matched
    """
    try:
        lines = session_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return

    session_id = session_path.stem

    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if obj.get("role") != "user":
            continue

        content = _extract_content(obj.get("content", ""))
        if content is None:
            continue

        if len(content) < MIN_LENGTH:
            continue
        if has_secret(content):
            continue
        if not KEYWORD_RE.search(content):
            continue

        yield {
            "ts": obj.get("ts", "unknown"),
            "session": session_id[:8],
            "text": content,
        }


# ---------------------------------------------------------------------------
# Suggestion enrichment
# ---------------------------------------------------------------------------

def suggest_links(text: str, graph_path: Path | None) -> list[str]:
    """Return node labels that appear in text.

    1. Extract [[WikiLink]] patterns directly from text.
    2. If graph_path exists, match node labels from graph.json against text.
    """
    found: set[str] = set()

    for m in _WIKILINK_RE.finditer(text):
        found.add(m.group(1))

    if graph_path and graph_path.exists():
        try:
            data = json.loads(graph_path.read_text(encoding="utf-8"))
            for node in data.get("nodes", []):
                label = node.get("label", "")
                if label and re.search(r"\b" + re.escape(label) + r"\b", text):
                    found.add(label)
        except (json.JSONDecodeError, OSError):
            pass

    return sorted(found)


def suggest_tags(text: str) -> list[str]:
    """Return tag names inferred from decision/rationale keyword heuristics."""
    tags: set[str] = set()
    for pattern, tag in _TAG_MAP:
        if pattern.search(text):
            tags.add(tag)
    return sorted(tags)
