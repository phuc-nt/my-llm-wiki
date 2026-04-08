# extract doc comments (Javadoc, JSDoc, GoDoc, Rust ///, etc.) from source files
# Attaches comment text to the nearest class/function node as a description
from __future__ import annotations
import re
from pathlib import Path


# Language-specific doc comment patterns
_PATTERNS: dict[str, list[re.Pattern]] = {
    # Java, Kotlin, Scala, PHP: /** ... */
    ".java": [re.compile(r'/\*\*\s*([\s\S]*?)\*/', re.MULTILINE)],
    ".kt": [re.compile(r'/\*\*\s*([\s\S]*?)\*/', re.MULTILINE)],
    ".kts": [re.compile(r'/\*\*\s*([\s\S]*?)\*/', re.MULTILINE)],
    ".scala": [re.compile(r'/\*\*\s*([\s\S]*?)\*/', re.MULTILINE)],
    ".php": [re.compile(r'/\*\*\s*([\s\S]*?)\*/', re.MULTILINE)],
    # JavaScript, TypeScript: /** ... */
    ".js": [re.compile(r'/\*\*\s*([\s\S]*?)\*/', re.MULTILINE)],
    ".ts": [re.compile(r'/\*\*\s*([\s\S]*?)\*/', re.MULTILINE)],
    ".tsx": [re.compile(r'/\*\*\s*([\s\S]*?)\*/', re.MULTILINE)],
    # Go: // line comments before func/type
    ".go": [re.compile(r'((?:^//[^\n]*\n)+)(?=\s*(?:func|type)\s)', re.MULTILINE)],
    # Rust: /// line comments
    ".rs": [re.compile(r'((?:^///[^\n]*\n)+)(?=\s*(?:pub\s+)?(?:fn|struct|enum|trait)\s)', re.MULTILINE)],
    # C#: /// XML doc comments
    ".cs": [re.compile(r'((?:^///[^\n]*\n)+)(?=\s*(?:public|private|protected|internal)\s)', re.MULTILINE)],
    # C/C++: /** ... */ or /// comments
    ".c": [re.compile(r'/\*\*\s*([\s\S]*?)\*/', re.MULTILINE)],
    ".cpp": [re.compile(r'/\*\*\s*([\s\S]*?)\*/', re.MULTILINE)],
    ".h": [re.compile(r'/\*\*\s*([\s\S]*?)\*/', re.MULTILINE)],
    ".hpp": [re.compile(r'/\*\*\s*([\s\S]*?)\*/', re.MULTILINE)],
    # Swift: /// line comments
    ".swift": [re.compile(r'((?:^///[^\n]*\n)+)(?=\s*(?:public\s+|private\s+|internal\s+|open\s+)?(?:func|class|struct|enum|protocol)\s)', re.MULTILINE)],
    # Ruby: # comments (yard-style, less reliable)
    ".rb": [re.compile(r'((?:^#[^\n]*\n)+)(?=\s*(?:def|class|module)\s)', re.MULTILINE)],
}


def _clean_comment(text: str) -> str:
    """Strip comment markers and normalize whitespace."""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        line = line.strip()
        # Strip leading *, //, ///, #
        line = re.sub(r'^[\s*/]+', '', line)
        line = re.sub(r'^///?', '', line)
        line = re.sub(r'^#', '', line)
        line = line.strip()
        # Skip @param, @return, @throws annotations
        if line.startswith('@') or line.startswith('<'):
            continue
        if line:
            cleaned.append(line)
    result = ' '.join(cleaned)
    # Truncate long comments
    if len(result) > 200:
        result = result[:200].rsplit(' ', 1)[0] + '...'
    return result


def extract_doc_comments(path: Path) -> list[dict]:
    """Extract doc comments from a source file.

    Returns list of {text, line_number} for each doc comment found.
    """
    ext = path.suffix.lower()
    patterns = _PATTERNS.get(ext)
    if not patterns:
        return []

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    comments = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            cleaned = _clean_comment(match.group(1) if match.lastindex else match.group(0))
            if len(cleaned) < 10:
                continue
            # Calculate line number
            line_no = text[:match.start()].count('\n') + 1
            comments.append({"text": cleaned, "line": line_no})

    return comments


def enrich_nodes_with_comments(
    nodes: list[dict],
    edges: list[dict],
    paths: list[Path],
) -> None:
    """Enrich existing AST nodes with doc comment descriptions.

    For each source file, extract doc comments and attach them to the nearest
    node (by line number) as a 'description' field.
    """
    # Build lookup: (source_file, approx_line) → node
    file_nodes: dict[str, list[dict]] = {}
    for node in nodes:
        sf = node.get("source_file", "")
        if sf:
            file_nodes.setdefault(sf, []).append(node)

    for path in paths:
        comments = extract_doc_comments(path)
        if not comments:
            continue

        str_path = str(path)
        # Try relative paths too
        matching_nodes = file_nodes.get(str_path, [])
        if not matching_nodes:
            for key in file_nodes:
                if key.endswith(str(path.name)):
                    matching_nodes = file_nodes[key]
                    break
        if not matching_nodes:
            continue

        # Sort nodes by line number
        sorted_nodes = sorted(
            [n for n in matching_nodes if n.get("source_location", "").startswith("L")],
            key=lambda n: int(n["source_location"][1:]) if n.get("source_location", "").startswith("L") else 0
        )

        for comment in comments:
            comment_line = comment["line"]
            # Find the nearest node AFTER this comment
            best_node = None
            for node in sorted_nodes:
                loc = node.get("source_location", "")
                if loc.startswith("L"):
                    node_line = int(loc[1:])
                    if node_line >= comment_line:
                        best_node = node
                        break
            if best_node and "description" not in best_node:
                best_node["description"] = comment["text"]
