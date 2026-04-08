# per-file extraction cache — skip unchanged files on re-run
from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

from my_llm_wiki.constants import OUTPUT_DIR


# Bump this when extraction output format changes (e.g., new fields like 'signature').
# Old cache entries without this version are treated as stale and re-extracted.
_CACHE_VERSION = 2


def file_hash(path: Path) -> str:
    """SHA256 of file contents + resolved path + cache version."""
    p = Path(path)
    h = hashlib.sha256()
    h.update(p.read_bytes())
    h.update(b"\x00")
    h.update(str(p.resolve()).encode())
    h.update(f"\x00v{_CACHE_VERSION}".encode())
    return h.hexdigest()


def cache_dir(root: Path = Path(".")) -> Path:
    """Returns wiki-out/cache/ — creates if needed."""
    d = Path(root) / OUTPUT_DIR / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_cached(path: Path, root: Path = Path(".")) -> dict | None:
    """Return cached extraction for this file if hash matches, else None."""
    try:
        h = file_hash(path)
    except OSError:
        return None
    entry = cache_dir(root) / f"{h}.json"
    if not entry.exists():
        return None
    try:
        return json.loads(entry.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_cached(path: Path, result: dict, root: Path = Path(".")) -> None:
    """Save extraction result keyed by SHA256 of current file contents."""
    h = file_hash(path)
    entry = cache_dir(root) / f"{h}.json"
    tmp = entry.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(result), encoding="utf-8")
        os.replace(tmp, entry)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def cached_files(root: Path = Path(".")) -> set[str]:
    """Return set of cache entry hashes."""
    d = cache_dir(root)
    return {p.stem for p in d.glob("*.json")}


def clear_cache(root: Path = Path(".")) -> None:
    """Delete all cache entries."""
    d = cache_dir(root)
    for f in d.glob("*.json"):
        f.unlink()


def check_semantic_cache(
    files: list[str],
    root: Path = Path("."),
) -> tuple[list[dict], list[dict], list[dict], list[str]]:
    """Check semantic extraction cache for a list of absolute file paths.

    Returns (cached_nodes, cached_edges, cached_hyperedges, uncached_files).
    """
    cached_nodes: list[dict] = []
    cached_edges: list[dict] = []
    cached_hyperedges: list[dict] = []
    uncached: list[str] = []

    for fpath in files:
        result = load_cached(Path(fpath), root)
        if result is not None:
            cached_nodes.extend(result.get("nodes", []))
            cached_edges.extend(result.get("edges", []))
            cached_hyperedges.extend(result.get("hyperedges", []))
        else:
            uncached.append(fpath)

    return cached_nodes, cached_edges, cached_hyperedges, uncached


def save_semantic_cache(
    nodes: list[dict],
    edges: list[dict],
    hyperedges: list[dict] | None = None,
    root: Path = Path("."),
) -> int:
    """Save semantic extraction results to cache, keyed by source_file.

    Returns the number of files cached.
    """
    by_file: dict[str, dict] = defaultdict(lambda: {"nodes": [], "edges": [], "hyperedges": []})
    for n in nodes:
        src = n.get("source_file", "")
        if src:
            by_file[src]["nodes"].append(n)
    for e in edges:
        src = e.get("source_file", "")
        if src:
            by_file[src]["edges"].append(e)
    for h in (hyperedges or []):
        src = h.get("source_file", "")
        if src:
            by_file[src]["hyperedges"].append(h)

    saved = 0
    for fpath, result in by_file.items():
        p = Path(fpath)
        if p.exists():
            save_cached(p, result, root)
            saved += 1
    return saved
