# Save LLM-session insights as markdown into wiki-out/ingested/.
# These files are picked up on the next `llm-wiki .` rebuild and folded
# into the graph — closing the Karpathy write-back loop.
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path


_MAX_TITLE_LEN = 80
_MAX_SLUG_LEN = 40

# Secret / PII patterns checked against note body before writing.
# These are noisy by design — better to false-positive than leak a key.
# Each entry: (pattern, short label for error message).
_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Private key blocks (PEM)
    (re.compile(r"-----BEGIN\s+(?:RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----"), "PEM private key"),
    # AWS access key ID
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    # AWS secret access key (40 base64 chars after "aws_secret" or similar)
    (re.compile(r"(?i)aws[_\-]?secret[_\-]?access[_\-]?key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}"), "AWS secret"),
    # Generic API key / token assignments with long opaque values
    (re.compile(r"(?i)(?:api[_\-]?key|secret|token|password|passwd|bearer)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}"), "API key/token assignment"),
    # GitHub personal access token
    (re.compile(r"\bghp_[A-Za-z0-9]{36,}\b"), "GitHub token"),
    # GitHub fine-grained PAT
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}\b"), "GitHub fine-grained PAT"),
    # Slack bot/user token
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}"), "Slack token"),
    # Google API key
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), "Google API key"),
    # JWT (three base64 segments)
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"), "JWT token"),
]


def _scan_for_secrets(text: str) -> str | None:
    """Return a label of the first secret pattern matched, or None if clean."""
    for pattern, label in _SECRET_PATTERNS:
        if pattern.search(text):
            return label
    return None


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
    allow_secrets: bool = False,
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
        allow_secrets: Skip secret scanning. Only set if you're sure. Default False.

    Returns:
        Path to the saved markdown file.

    Raises:
        ValueError: if text is empty, or if secret-like content detected and
            allow_secrets is False.
    """
    clean_text = text.strip()
    if not clean_text:
        raise ValueError("note text is empty")

    # Scan for secrets before writing anything to disk
    if not allow_secrets:
        secret_label = _scan_for_secrets(clean_text)
        if secret_label:
            raise ValueError(
                f"note content appears to contain a secret ({secret_label}). "
                f"Redact it, or pass allow_secrets=True if this is a false positive."
            )

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
