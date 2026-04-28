# capture.py — llm-wiki capture: scan Claude Code session jsonl for note candidates
# Batch-only, opt-in. No network calls. Stdlib only.
# Filtering logic lives in capture-filters.py (split per 200-LOC rule).
from __future__ import annotations

import importlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Lazy import of filters module (kebab-case module loaded via importlib)
_filters = importlib.import_module("my_llm_wiki.capture-filters")

# Re-export private aliases used by tests
_has_secret = _filters.has_secret
_iter_candidates = _filters.iter_candidates
_suggest_links = _filters.suggest_links
_suggest_tags = _filters.suggest_tags

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_FLAG_REL = Path("cache") / "capture-enabled"
_OUTPUT_REL = Path("captured") / "pending-notes.md"


# ---------------------------------------------------------------------------
# Enable-flag helpers
# ---------------------------------------------------------------------------

def _check_enabled(wiki_out: Path) -> bool:
    """Return True iff the capture-enabled flag file exists."""
    return (wiki_out / _FLAG_REL).exists()


def _enable(wiki_out: Path) -> None:
    """Create the opt-in flag file (idempotent)."""
    flag = wiki_out / _FLAG_REL
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.touch(exist_ok=True)


# ---------------------------------------------------------------------------
# Session resolver
# ---------------------------------------------------------------------------

def _find_sessions(
    project_cwd: Path,
    since: timedelta,
    claude_home: Path | None = None,
) -> list[Path]:
    """Walk ~/.claude/projects/ and return jsonl paths whose cwd matches project_cwd
    and whose mtime falls within the 'since' window.

    Respects CLAUDE_HOME env var; defaults to ~/.claude/projects/.
    """
    if claude_home is None:
        env_home = os.environ.get("CLAUDE_HOME")
        claude_home = Path(env_home) / "projects" if env_home else Path.home() / ".claude" / "projects"

    if not claude_home.exists():
        return []

    cutoff = datetime.now(tz=timezone.utc) - since
    cwd_str = str(project_cwd.resolve())
    result: list[Path] = []

    for jsonl in claude_home.rglob("*.jsonl"):
        try:
            mtime = datetime.fromtimestamp(jsonl.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue
        if mtime < cutoff:
            continue

        # cwd match: read first line only (cheap)
        try:
            with jsonl.open(encoding="utf-8", errors="replace") as fh:
                first_line = fh.readline().strip()
        except OSError:
            continue
        try:
            header = json.loads(first_line)
        except json.JSONDecodeError:
            continue

        if str(header.get("cwd", "")) == cwd_str:
            result.append(jsonl)

    return result


# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------

def _write_pending(candidates: list[dict], output_path: Path) -> None:
    """Write candidate notes to output_path in the spec markdown format."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not candidates:
        output_path.write_text(
            "# Captured Session Notes\n\n_No candidates found._\n",
            encoding="utf-8",
        )
        return

    lines: list[str] = ["# Captured Session Notes\n"]
    for c in candidates:
        ts = c.get("ts", "unknown")
        session = c.get("session", "unknown")
        text = c.get("text", "")
        links: list[str] = c.get("suggested_links", [])
        tags: list[str] = c.get("suggested_tags", [])

        lines.append(f"## [{ts}] [{session}]")
        lines.append(f"Suggested note: {text[:200].strip()}")

        link_str = " ".join(f"--link {lnk}" for lnk in links) if links else "(none)"
        lines.append(f"Suggested links: {link_str}")

        tag_str = " ".join(f"--tag {t}" for t in tags) if tags else "(none)"
        lines.append(f"Suggested tags: {tag_str}")

        excerpt = text[:300].replace("\n", " ").strip()
        lines.append(f"Source excerpt: > {excerpt}")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def capture(
    project_cwd: Path,
    wiki_out: Path,
    since_hours: float = 24,
    enable: bool = False,
    claude_home: Path | None = None,
) -> None:
    """Run the capture pipeline.

    Args:
        project_cwd:  Root of the project whose sessions to scan.
        wiki_out:     Path to wiki-out directory (flag lives here; output written here).
        since_hours:  Scan window in hours (default 24).
        enable:       If True, write the opt-in flag file and return immediately.
        claude_home:  Override for ~/.claude/projects parent directory.
    """
    if enable:
        _enable(wiki_out)
        print("[wiki] Capture enabled. Run `llm-wiki capture` to scan sessions.")
        return

    if not _check_enabled(wiki_out):
        print(
            "[wiki] Capture is not enabled.\n"
            "  Run `llm-wiki capture --enable` to opt in.\n"
            "  This command scans Claude Code session logs — opt-in is required for privacy."
        )
        sys.exit(1)

    since = timedelta(hours=since_hours)
    sessions = _find_sessions(project_cwd, since, claude_home=claude_home)
    graph_path = wiki_out / "graph.json"

    candidates: list[dict] = []
    for session_path in sessions:
        for c in _iter_candidates(session_path):
            c["suggested_links"] = _suggest_links(c["text"], graph_path)
            c["suggested_tags"] = _suggest_tags(c["text"])
            candidates.append(c)

    output_path = wiki_out / _OUTPUT_REL
    _write_pending(candidates, output_path)

    if candidates:
        print(f"[wiki] {len(candidates)} candidate(s) written to {output_path}")
        print("[wiki] Review and promote with `llm-wiki note`.")
    else:
        print("[wiki] No candidates found. pending-notes.md written with empty result.")
