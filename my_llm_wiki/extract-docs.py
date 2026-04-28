# extract entities and relationships from markdown/text documents
# Structural extraction: headings, links, cross-references, key terms
# No LLM required — deterministic, fast, free
from __future__ import annotations
import hashlib
import re
from pathlib import Path


# Markdown link: [text](url) or [text](file.md)
_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

# List items that look like definitions: - **Term**: description
_DEFINITION_RE = re.compile(r'^[\s]*[-*]\s+\*\*([^*]+)\*\*[:\s]', re.MULTILINE)

# Standalone bold line as a heading fallback (D7). Matches a single line
# whose entire content is **...** with 1-80 chars inside. Used only when a
# document has no markdown # headings — many real-world DOCX/PDF files use
# inline bold for titles instead of Heading 1/2 styles. Roman numerals like
# **I**, **II** are valid section markers, hence min length 1.
_BOLD_HEADING_RE = re.compile(r'^\s*\*\*([^*\n]{1,80})\*\*\s*$')
_HEADING_TRAILING_PUNCT = (".", ",", ":", ";", "?", "!")

# Generic headings that don't carry domain-specific meaning — skip for cross-doc matching
_GENERIC_HEADINGS = {
    "next steps", "troubleshooting", "examples", "overview", "summary",
    "getting started", "prerequisites", "installation", "usage", "faq",
    "best practices", "common issues", "see also", "references", "notes",
    "tips", "configuration", "setup", "introduction", "conclusion",
}


def _make_id(source_file: str, label: str) -> str:
    """Create a deterministic node ID from source file + label."""
    raw = f"{source_file}::{label}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _extract_headings(text: str) -> list[tuple[int, str, int]]:
    """Extract (level, title, line_number) from markdown headings.
    Skips headings inside fenced code blocks.

    Fallback (D7): if zero ``#``-style headings exist, treat standalone
    ``**bold**`` lines (2-80 chars, no trailing punctuation) as h1 headings.
    Common in DOCX/PDF that use inline bold instead of Heading 1/2 styles.
    """
    headings = []
    bold_candidates: list[tuple[int, str, int]] = []
    in_code_block = False
    for i, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        m = re.match(r'^(#{1,4})\s+(.+)$', line)
        if m:
            title = m.group(2).strip()
            if not _is_noisy_term(title):
                headings.append((len(m.group(1)), title, i))
            continue
        bm = _BOLD_HEADING_RE.match(line)
        if bm:
            title = bm.group(1).strip()
            if title.endswith(_HEADING_TRAILING_PUNCT):
                continue
            bold_candidates.append((1, title, i))

    if headings:
        return headings
    return bold_candidates


def _extract_links(text: str) -> list[tuple[str, str]]:
    """Extract (link_text, target) from markdown links."""
    return [(m.group(1), m.group(2)) for m in _LINK_RE.finditer(text)]


def _strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks to avoid extracting code snippets as entities."""
    return re.sub(r'```[\s\S]*?```', '', text)


def _is_noisy_term(term: str) -> bool:
    """Filter out terms that look like code output, table rows, or noise."""
    if len(term) > 40 or len(term) < 2:
        return True
    # Reject non-printable / control characters
    if any(ord(c) < 32 and c not in '\n\r\t' for c in term):
        return True
    # Table-like content: multiple spaces, tabs, columns
    if '  ' in term or '\t' in term:
        return True
    # Looks like a file path, variable, or code
    if any(c in term for c in ['/', '\\', '=', '{', '}', '(', ')', '[', ']']):
        return True
    # Mostly digits or punctuation
    alpha = sum(1 for c in term if c.isalpha())
    if alpha < len(term) * 0.5:
        return True
    return False


def _extract_definitions(text: str) -> list[str]:
    """Extract defined terms from list items like '- **Term**: description'."""
    clean = _strip_code_blocks(text)
    terms = []
    for m in _DEFINITION_RE.finditer(clean):
        term = m.group(1).strip()
        if _is_noisy_term(term):
            continue
        terms.append(term)
    return terms


def _normalize_link_target(target: str, source_file: str) -> str | None:
    """Resolve relative markdown links to file paths. Returns None for external URLs."""
    if target.startswith(('http://', 'https://', '#', 'mailto:')):
        return None
    # Strip anchors: file.md#section -> file.md
    target = target.split('#')[0]
    if not target:
        return None
    # Resolve relative to source file directory, normalize path
    source_dir = Path(source_file).parent
    resolved = (source_dir / target).as_posix()
    # Normalize: remove leading ./ and resolve ..
    parts = []
    for part in resolved.split('/'):
        if part == '.' or not part:
            continue
        if part == '..' and parts:
            parts.pop()
        else:
            parts.append(part)
    return '/'.join(parts) if parts else None


def _pdf_page_count(path: Path) -> int:
    """Return the page count of a PDF, preferring Docling when available."""
    try:
        import importlib
        docling = importlib.import_module("my_llm_wiki.extract-with-docling")
        if docling.is_docling_available():
            result = docling.extract_with_docling(path)
            if not result.get("error"):
                return int(result.get("page_count") or 0)
    except Exception:
        pass
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(path)).pages)
    except Exception:
        return 0


# Extensions where Docling provides per-heading page numbers.
# EPUB uses chapter order, not page numbers — excluded intentionally.
_DOCLING_PAGE_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".htm"}


def _docling_headings(path: Path) -> list[dict] | None:
    """Return Docling-sourced headings (with page) for supported file types.

    Returns a list of {level, text, page} dicts when Docling is available and
    the file extension supports per-heading page numbers. Returns None when
    Docling is unavailable, the file type is not supported, or extraction fails
    — callers fall back to text-based heading extraction.
    """
    if path.suffix.lower() not in _DOCLING_PAGE_EXTENSIONS:
        return None
    try:
        import importlib
        docling_mod = importlib.import_module("my_llm_wiki.extract-with-docling")
        if not docling_mod.is_docling_available():
            return None
        result = docling_mod.extract_with_docling(path)
        if result.get("error") or not result.get("headings"):
            return None
        return result["headings"]  # list of {level, text, page}
    except Exception:
        return None


def _read_file_text(path: Path) -> str:
    """Read file content as text. Routes through office converters for
    PDF/DOCX/PPTX/HTML so the Docling pipeline (when installed) is used
    consistently. Falls back to UTF-8 read for plain text files.
    """
    ext = path.suffix.lower()
    if ext == ".pdf":
        import importlib
        office = importlib.import_module("my_llm_wiki.detect-office-convert")
        return office.extract_pdf_text(path)
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def extract_doc(path: Path, root: Path | None = None) -> dict:
    """Extract nodes and edges from a single markdown/text document.

    Returns same format as AST extractor: {"nodes": [...], "edges": [...]}
    """
    text = _read_file_text(path)
    if not text.strip():
        # No extractable text — create minimal hub node only
        str_path = str(path.relative_to(root)) if root else str(path)
        doc_name = path.stem
        doc_id = _make_id(str_path, doc_name)
        return {"nodes": [{
            "id": doc_id, "label": doc_name,
            "file_type": "paper" if path.suffix.lower() == ".pdf" else "document",
            "source_file": str_path, "source_location": "L1",
        }], "edges": []}

    str_path = str(path.relative_to(root)) if root else str(path)
    nodes: list[dict] = []
    edges: list[dict] = []
    seen_ids: set[str] = set()

    is_pdf = path.suffix.lower() == ".pdf"
    file_type = "paper" if is_pdf else "document"

    # Document hub node
    doc_name = path.stem
    doc_id = _make_id(str_path, doc_name)
    hub_node: dict = {
        "id": doc_id, "label": doc_name, "file_type": file_type,
        "source_file": str_path, "source_location": "L1",
    }
    if is_pdf:
        page_count = _pdf_page_count(path)
        if page_count:
            hub_node["pages"] = page_count
    nodes.append(hub_node)
    seen_ids.add(doc_id)

    # Extract h1/h2 headings as section nodes (h3+ too granular).
    # Prefer Docling headings (carry per-heading page numbers) for supported
    # file types; fall back to text-based extraction for markdown/plain text.
    docling_hdrs = _docling_headings(path)
    if docling_hdrs is not None:
        # Build (level, title, page_or_None, location) from Docling output.
        # source_location uses page ref; page attr carries the 1-indexed page number.
        raw_headings: list[tuple[int, str, int | None, str]] = [
            (h["level"], h["text"], h.get("page"),
             f"p{h['page']}" if h.get("page") else "L1")
            for h in docling_hdrs
            if not _is_noisy_term(h.get("text", ""))
        ]
    else:
        # Text-based fallback: preserve original line-number location; no page attr.
        raw_headings = [
            (lvl, title, None, f"L{ln}") for lvl, title, ln in _extract_headings(text)
        ]

    parent_stack: list[tuple[int, str]] = [(0, doc_id)]  # doc is root
    for level, title, page, location in raw_headings:
        if level > 2:
            continue
        section_id = _make_id(str_path, title)
        if section_id in seen_ids:
            continue
        seen_ids.add(section_id)
        node: dict = {
            "id": section_id, "label": title, "file_type": file_type,
            "source_file": str_path, "source_location": location,
        }
        if page is not None:
            node["page"] = int(page)
        nodes.append(node)
        # Find parent: pop until we find lower level
        while len(parent_stack) > 1 and parent_stack[-1][0] >= level:
            parent_stack.pop()
        edges.append({
            "source": parent_stack[-1][1], "target": section_id,
            "relation": "contains", "confidence": "EXTRACTED",
            "source_file": str_path,
        })
        parent_stack.append((level, section_id))

    # Extract defined terms as concept nodes
    definitions = _extract_definitions(text)
    for term in definitions[:20]:  # cap to avoid noise
        term_id = _make_id(str_path, term)
        if term_id in seen_ids:
            continue
        seen_ids.add(term_id)
        nodes.append({
            "id": term_id, "label": term, "file_type": "document",
            "source_file": str_path, "source_location": "",
        })
        edges.append({
            "source": doc_id, "target": term_id,
            "relation": "defines", "confidence": "EXTRACTED",
            "source_file": str_path,
        })

    # Extract cross-doc links (deduplicate targets)
    links = _extract_links(_strip_code_blocks(text))
    seen_link_targets: set[str] = set()
    for link_text, target in links:
        resolved = _normalize_link_target(target, str_path)
        if not resolved or resolved in seen_link_targets:
            continue
        seen_link_targets.add(resolved)
        # Create a placeholder node for the link target — will be merged in build
        link_target_id = _make_id(resolved, Path(resolved).stem)
        if link_target_id not in seen_ids:
            seen_ids.add(link_target_id)
            nodes.append({
                "id": link_target_id, "label": Path(resolved).stem,
                "file_type": "document",
                "source_file": resolved, "source_location": "",
            })
        edges.append({
            "source": doc_id, "target": link_target_id,
            "relation": "references", "confidence": "EXTRACTED",
            "source_file": str_path,
        })

    return {"nodes": nodes, "edges": edges}


def extract_docs(paths: list[Path], root: Path | None = None) -> dict:
    """Extract from multiple document files. Returns combined {nodes, edges}."""
    all_nodes: list[dict] = []
    all_edges: list[dict] = []

    for path in paths:
        result = extract_doc(path, root)
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])

    # Cross-doc: find shared defined terms across documents
    _add_cross_doc_edges(all_nodes, all_edges)

    return {"nodes": all_nodes, "edges": all_edges}


def _add_cross_doc_edges(nodes: list[dict], edges: list[dict]) -> None:
    """Add edges between documents that share the same defined terms."""
    # Group nodes by label (case-insensitive), skip generic headings
    label_to_nodes: dict[str, list[dict]] = {}
    for node in nodes:
        key = node["label"].lower().strip()
        if len(key) < 3 or key in _GENERIC_HEADINGS:
            continue
        label_to_nodes.setdefault(key, []).append(node)

    # If same label appears in multiple files, link them
    for label, group in label_to_nodes.items():
        sources = list({n["source_file"] for n in group})
        if len(sources) <= 1:
            continue
        # Link first occurrence to others
        primary = group[0]
        for other in group[1:]:
            if other["source_file"] != primary["source_file"]:
                edges.append({
                    "source": primary["id"], "target": other["id"],
                    "relation": "same_concept", "confidence": "INFERRED",
                    "source_file": primary["source_file"],
                })
