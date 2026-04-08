# Save LLM-session insights as markdown into wiki-out/ingested/.
# These files are picked up on the next `llm-wiki .` rebuild and folded
# into the graph — closing the Karpathy write-back loop.
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


_MAX_TITLE_LEN = 80
_MAX_SLUG_LEN = 40


def _slugify(text: str) -> str:
    """Turn arbitrary text into a safe filename fragment."""
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return text[:_MAX_SLUG_LEN].rstrip("-") or "note"


def _fmt_list(items: list[str]) -> str:
    """YAML inline list: [a, b, c]."""
    return "[" + ", ".join(items) + "]"


def write_note(
    text: str,
    *,
    output_dir: str = "wiki-out/ingested",
    title: str | None = None,
    links: list[str] | None = None,
    tags: list[str] | None = None,
) -> Path:
    """Save an insight as markdown for the next rebuild to ingest.

    Body is the text verbatim. Optional title/links/tags go into YAML
    frontmatter. Link names are echoed as `[[WikiLinks]]` in the body so
    the cross-reference pass picks them up as `mentions` edges.

    Args:
        text: The insight content (required, will be stripped).
        output_dir: Where to write the note (default: wiki-out/ingested).
        title: Optional heading. If omitted, derived from first line.
        links: Node labels this insight relates to (e.g. ["GraphStore"]).
        tags: Free-form tags (e.g. ["decision", "cache"]).

    Returns:
        Path to the saved markdown file.

    Raises:
        ValueError: if text is empty after stripping.
    """
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("note text is empty")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    # Use second-resolution timestamp so concurrent notes don't collide
    date_str = now.strftime("%Y%m%d-%H%M%S")

    heading = (title or clean_text.split("\n", 1)[0])[:_MAX_TITLE_LEN].strip()
    slug = _slugify(heading)
    path = out / f"note-{date_str}-{slug}.md"

    # YAML frontmatter
    fm: list[str] = [
        "---",
        "type: insight",
        f"date: {now.isoformat()}",
    ]
    if tags:
        fm.append(f"tags: {_fmt_list(tags)}")
    if links:
        fm.append(f"links: {_fmt_list(links)}")
    fm.append("---")

    # Markdown body
    body_parts: list[str] = [f"# {heading}", "", clean_text]
    if links:
        wikilinks = ", ".join(f"[[{L}]]" for L in links)
        body_parts.extend(["", f"**Related:** {wikilinks}"])

    content = "\n".join(fm) + "\n\n" + "\n".join(body_parts) + "\n"
    path.write_text(content, encoding="utf-8")
    return path
