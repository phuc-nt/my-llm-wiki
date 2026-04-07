# fetch URLs and save as markdown for wiki ingestion
# Supports: web pages, PDF links, plain text
from __future__ import annotations
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path


def _fetch_text(url: str) -> str:
    """Fetch URL content as text."""
    req = urllib.request.Request(url, headers={"User-Agent": "my-llm-wiki/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        content_type = resp.headers.get("Content-Type", "")
        data = resp.read()
        if "pdf" in content_type.lower():
            return _pdf_bytes_to_text(data)
        encoding = "utf-8"
        if "charset=" in content_type:
            encoding = content_type.split("charset=")[-1].split(";")[0].strip()
        return data.decode(encoding, errors="ignore")


def _pdf_bytes_to_text(data: bytes) -> str:
    """Convert PDF bytes to text using pypdf if available."""
    try:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        return "[PDF content — install pypdf to extract text: pip install my-llm-wiki[pdf]]"


def _html_to_markdown(html: str) -> str:
    """Convert HTML to markdown. Uses html2text if available, else strip tags."""
    try:
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.body_width = 0
        return h.handle(html)
    except ImportError:
        # Basic tag stripping fallback
        text = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', html)
        text = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', text)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text


def _safe_filename(url: str) -> str:
    """Convert URL to a safe filename."""
    name = re.sub(r'https?://', '', url)
    name = re.sub(r'[^\w\-.]', '_', name)
    return name[:80].rstrip("_") + ".md"


def ingest(url: str, output_dir: str = "wiki-out/ingested",
           author: str | None = None) -> Path:
    """Fetch a URL and save as markdown with YAML frontmatter.

    Returns the path to the saved file.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[wiki] Fetching {url} ...")
    raw = _fetch_text(url)

    # Convert HTML to markdown
    if "<html" in raw.lower()[:500] or "<body" in raw.lower()[:500]:
        text = _html_to_markdown(raw)
    else:
        text = raw

    # Build frontmatter
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "---",
        f'source_url: "{url}"',
        f'captured_at: "{now}"',
    ]
    if author:
        lines.append(f'author: "{author}"')
    lines += ["---", "", text]

    filename = _safe_filename(url)
    path = out / filename
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[wiki] Saved to {path}")
    return path
