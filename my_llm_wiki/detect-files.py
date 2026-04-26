# file discovery, type classification, and corpus health checks
from __future__ import annotations

import fnmatch
import importlib
import os
import re
from enum import Enum
from pathlib import Path

from my_llm_wiki.constants import OUTPUT_DIR

# Import office conversion helper
_office_mod = importlib.import_module("my_llm_wiki.detect-office-convert")
convert_office_file = _office_mod.convert_office_file
extract_pdf_text = _office_mod.extract_pdf_text
docx_to_markdown = _office_mod.docx_to_markdown
xlsx_to_markdown = _office_mod.xlsx_to_markdown
pptx_to_markdown = _office_mod.pptx_to_markdown
html_to_markdown = _office_mod.html_to_markdown


class FileType(str, Enum):
    CODE = "code"
    DOCUMENT = "document"
    PAPER = "paper"
    IMAGE = "image"


CODE_EXTENSIONS = {
    '.py', '.ts', '.js', '.tsx', '.go', '.rs', '.java',
    '.cpp', '.cc', '.cxx', '.c', '.h', '.hpp',
    '.rb', '.swift', '.kt', '.kts', '.cs', '.scala',
    '.php', '.lua', '.toc', '.zig', '.ps1', '.ex', '.exs',
}
DOC_EXTENSIONS = {'.md', '.txt', '.rst'}
PAPER_EXTENSIONS = {'.pdf'}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.heic', '.heif', '.tiff', '.bmp'}
OFFICE_EXTENSIONS = {'.docx', '.xlsx', '.pptx', '.html', '.htm'}

CORPUS_WARN_THRESHOLD = 50_000    # words - below this, warn "you may not need a graph"
CORPUS_UPPER_THRESHOLD = 500_000  # words - above this, warn about token cost
FILE_COUNT_UPPER = 200             # files - above this, warn about token cost

# Files that may contain secrets - skip silently
_SENSITIVE_PATTERNS = [
    re.compile(r'(^|[\\/])\.(env|envrc)(\.|$)', re.IGNORECASE),
    re.compile(r'\.(pem|key|p12|pfx|cert|crt|der|p8)$', re.IGNORECASE),
    re.compile(r'(credential|secret|passwd|password|token|private_key)', re.IGNORECASE),
    re.compile(r'(id_rsa|id_dsa|id_ecdsa|id_ed25519)(\.pub)?$'),
    re.compile(r'(\.netrc|\.pgpass|\.htpasswd)$', re.IGNORECASE),
    re.compile(r'(aws_credentials|gcloud_credentials|service.account)', re.IGNORECASE),
]

# Signals that a .md/.txt file is actually a converted academic paper
_PAPER_SIGNALS = [
    re.compile(r'\barxiv\b', re.IGNORECASE),
    re.compile(r'\bdoi\s*:', re.IGNORECASE),
    re.compile(r'\babstract\b', re.IGNORECASE),
    re.compile(r'\bproceedings\b', re.IGNORECASE),
    re.compile(r'\bjournal\b', re.IGNORECASE),
    re.compile(r'\bpreprint\b', re.IGNORECASE),
    re.compile(r'\\cite\{'),          # LaTeX citation
    re.compile(r'\[\d+\]'),           # Numbered citation [1], [23] (inline)
    re.compile(r'\[\n\d+\n\]'),       # Numbered citation spread across lines
    re.compile(r'eq\.\s*\d+|equation\s+\d+', re.IGNORECASE),
    re.compile(r'\d{4}\.\d{4,5}'),   # arXiv ID like 1706.03762
    re.compile(r'\bwe propose\b', re.IGNORECASE),
    re.compile(r'\bliterature\b', re.IGNORECASE),
]
_PAPER_SIGNAL_THRESHOLD = 3  # need at least this many signals to call it a paper


def _is_sensitive(path: Path) -> bool:
    """Return True if this file likely contains secrets and should be skipped."""
    name = path.name
    full = str(path)
    return any(p.search(name) or p.search(full) for p in _SENSITIVE_PATTERNS)


def _looks_like_paper(path: Path) -> bool:
    """Heuristic: does this text file read like an academic paper?"""
    try:
        text = path.read_text(errors="ignore")[:3000]
        hits = sum(1 for pattern in _PAPER_SIGNALS if pattern.search(text))
        return hits >= _PAPER_SIGNAL_THRESHOLD
    except Exception:
        return False


def classify_file(path: Path) -> FileType | None:
    ext = path.suffix.lower()
    if ext in CODE_EXTENSIONS:
        return FileType.CODE
    if ext in PAPER_EXTENSIONS:
        return FileType.PAPER
    if ext in IMAGE_EXTENSIONS:
        return FileType.IMAGE
    if ext in DOC_EXTENSIONS:
        if _looks_like_paper(path):
            return FileType.PAPER
        return FileType.DOCUMENT
    if ext in OFFICE_EXTENSIONS:
        return FileType.DOCUMENT
    return None


def count_words(path: Path) -> int:
    try:
        ext = path.suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            return 0  # images have no text words
        if ext == ".pdf":
            return len(extract_pdf_text(path).split())
        if ext == ".docx":
            return len(docx_to_markdown(path).split())
        if ext == ".xlsx":
            return len(xlsx_to_markdown(path).split())
        if ext == ".pptx":
            return len(pptx_to_markdown(path).split())
        if ext in (".html", ".htm"):
            return len(html_to_markdown(path).split())
        return len(path.read_text(errors="ignore").split())
    except Exception:
        return 0


# Directory names to always skip - venvs, caches, build artifacts, deps
_SKIP_DIRS = {
    "venv", ".venv", "env", ".env",
    "node_modules", "__pycache__", ".git",
    "dist", "build", "target", "out",
    "site-packages", "lib64",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", ".eggs", "*.egg-info",
    OUTPUT_DIR,  # skip own output directory (wiki-out)
}


def _is_noise_dir(part: str) -> bool:
    """Return True if this directory name looks like a venv, cache, or dep dir."""
    if part in _SKIP_DIRS:
        return True
    if part.endswith("_venv") or part.endswith("_env"):
        return True
    if part.endswith(".egg-info"):
        return True
    return False


def _load_wikiignore(root: Path) -> list[str]:
    """Read .wikiignore from root and return a list of patterns.

    Lines starting with # are comments. Blank lines are ignored.
    Patterns follow gitignore semantics: glob matched against the path
    relative to root. A leading slash anchors to root. A trailing slash
    matches directories only (we match both dir and file for simplicity).
    """
    ignore_file = root / ".wikiignore"
    if not ignore_file.exists():
        return []
    patterns = []
    for line in ignore_file.read_text(errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def _is_ignored(path: Path, root: Path, patterns: list[str]) -> bool:
    """Return True if path matches any .wikiignore pattern."""
    if not patterns:
        return False
    try:
        rel = str(path.relative_to(root))
    except ValueError:
        return False
    rel = rel.replace(os.sep, "/")
    parts = rel.split("/")
    for pattern in patterns:
        p = pattern.strip("/")
        if not p:
            continue
        if fnmatch.fnmatch(rel, p):
            return True
        if fnmatch.fnmatch(path.name, p):
            return True
        for i, part in enumerate(parts):
            if fnmatch.fnmatch(part, p):
                return True
            if fnmatch.fnmatch("/".join(parts[:i + 1]), p):
                return True
    return False


def detect(root: Path) -> dict:
    files: dict[FileType, list[str]] = {
        FileType.CODE: [],
        FileType.DOCUMENT: [],
        FileType.PAPER: [],
        FileType.IMAGE: [],
    }
    total_words = 0
    skipped_sensitive: list[str] = []
    ignore_patterns = _load_wikiignore(root)

    # Always include wiki-out/memory/ and wiki-out/ingested/ even though wiki-out is skipped
    memory_dir = root / OUTPUT_DIR / "memory"
    ingested_dir = root / OUTPUT_DIR / "ingested"
    scan_paths = [root]
    if memory_dir.exists():
        scan_paths.append(memory_dir)
    if ingested_dir.exists():
        scan_paths.append(ingested_dir)

    seen: set[Path] = set()
    all_files: list[Path] = []

    for scan_root in scan_paths:
        in_memory_tree = memory_dir.exists() and str(scan_root).startswith(str(memory_dir))
        for dirpath, dirnames, filenames in os.walk(scan_root, followlinks=False):
            dp = Path(dirpath)
            if not in_memory_tree:
                dirnames[:] = [
                    d for d in dirnames
                    if not d.startswith(".")
                    and not _is_noise_dir(d)
                    and not _is_ignored(dp / d, root, ignore_patterns)
                ]
            for fname in filenames:
                p = dp / fname
                if p not in seen:
                    seen.add(p)
                    all_files.append(p)

    converted_dir = root / OUTPUT_DIR / "converted"

    for p in all_files:
        in_memory = memory_dir.exists() and str(p).startswith(str(memory_dir))
        if not in_memory:
            if p.name.startswith("."):
                continue
            if str(p).startswith(str(converted_dir)):
                continue
        if _is_ignored(p, root, ignore_patterns):
            continue
        if _is_sensitive(p):
            skipped_sensitive.append(str(p))
            continue
        ftype = classify_file(p)
        if ftype:
            if p.suffix.lower() in OFFICE_EXTENSIONS:
                md_path = convert_office_file(p, converted_dir)
                if md_path:
                    files[ftype].append(str(md_path))
                    total_words += count_words(md_path)
                else:
                    skipped_sensitive.append(str(p) + " [office conversion failed - pip install my-llm-wiki[office]]")
                continue
            files[ftype].append(str(p))
            total_words += count_words(p)

    total_files = sum(len(v) for v in files.values())
    needs_graph = total_words >= CORPUS_WARN_THRESHOLD

    warning: str | None = None
    if not needs_graph:
        warning = (
            f"Corpus is ~{total_words:,} words - fits in a single context window. "
            f"You may not need a graph."
        )
    elif total_words >= CORPUS_UPPER_THRESHOLD or total_files >= FILE_COUNT_UPPER:
        warning = (
            f"Large corpus: {total_files} files · ~{total_words:,} words. "
            f"Semantic extraction will be expensive (many tokens). "
            f"Consider running on a subfolder, or use --no-semantic to run AST-only."
        )

    return {
        "files": {k.value: v for k, v in files.items()},
        "total_files": total_files,
        "total_words": total_words,
        "needs_graph": needs_graph,
        "warning": warning,
        "skipped_sensitive": skipped_sensitive,
        "wikiignore_patterns": len(ignore_patterns),
    }
