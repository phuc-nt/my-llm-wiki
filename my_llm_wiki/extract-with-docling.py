# Docling adapter — wraps IBM Docling behind a stable internal dict shape.
# Lazy import only: base install must work without `docling`.
from __future__ import annotations

from pathlib import Path
from typing import Any


def is_docling_available() -> bool:
    """True if docling can be imported in the current environment."""
    try:
        import docling.document_converter  # noqa: F401
        return True
    except Exception:
        return False


def _empty_result(error: str | None = None) -> dict[str, Any]:
    return {
        "text": "",
        "headings": [],
        "tables": [],
        "page_count": 0,
        "error": error,
    }


def extract_with_docling(path: Path) -> dict[str, Any]:
    """Extract structured content from a document via Docling.

    Returns a normalized dict with keys: text, headings, tables, page_count, error.
    On any failure (missing docling, parse error, missing file) returns an
    empty result with `error` set — never raises.
    """
    path = Path(path)
    if not path.exists():
        return _empty_result(error=f"file not found: {path}")
    if not is_docling_available():
        return _empty_result(error="docling not installed (pip install my-llm-wiki[docling])")

    try:
        from docling.document_converter import DocumentConverter
        converter = DocumentConverter()
        conv_result = converter.convert(str(path))
        doc = conv_result.document
    except Exception as exc:
        return _empty_result(error=f"docling conversion failed: {exc}")

    return _normalize(doc)


def _normalize(doc: Any) -> dict[str, Any]:
    """Convert a docling document into our internal dict shape."""
    text = ""
    try:
        text = doc.export_to_markdown()
    except Exception:
        try:
            text = doc.export_to_text()
        except Exception:
            text = ""

    headings: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    page_count = 0

    # Walk the structured document if available
    iterate = getattr(doc, "iterate_items", None)
    if callable(iterate):
        for item, _level in iterate():
            kind = getattr(item, "label", None)
            if kind is None:
                continue
            kind_str = str(kind).lower()
            page = _first_page(item)
            if "section_header" in kind_str or "title" in kind_str:
                headings.append({
                    "level": getattr(item, "level", 1) or 1,
                    "text": _text_of(item),
                    "page": page,
                })
            elif "table" in kind_str:
                tables.append({
                    "text": _text_of(item),
                    "page": page,
                })

    pages = getattr(doc, "pages", None)
    if pages is not None:
        try:
            page_count = len(pages)
        except Exception:
            page_count = 0

    return {
        "text": text or "",
        "headings": headings,
        "tables": tables,
        "page_count": page_count,
        "error": None,
    }


def _text_of(item: Any) -> str:
    for attr in ("text", "orig", "name"):
        value = getattr(item, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _first_page(item: Any) -> int | None:
    prov = getattr(item, "prov", None)
    if not prov:
        return None
    try:
        first = prov[0]
        return getattr(first, "page_no", None) or getattr(first, "page", None)
    except Exception:
        return None
