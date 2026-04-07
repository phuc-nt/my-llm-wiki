# Python-specific post-processing: docstring/rationale extraction and cross-file import resolution
from __future__ import annotations

import importlib
from pathlib import Path

_core = importlib.import_module("my_llm_wiki.extract-core")
_make_id = _core._make_id

_RATIONALE_PREFIXES = (
    "# NOTE:", "# IMPORTANT:", "# HACK:", "# WHY:",
    "# RATIONALE:", "# TODO:", "# FIXME:",
)


def extract_python_rationale(path: Path, result: dict) -> None:
    """Post-pass: extract docstrings and rationale comments from Python source.
    Mutates result in-place by appending to result['nodes'] and result['edges'].
    """
    try:
        import tree_sitter_python as tspython
        from tree_sitter import Language, Parser
        language = Language(tspython.language())
        parser = Parser(language)
        source = path.read_bytes()
        root = parser.parse(source).root_node
    except Exception:
        return

    stem = path.stem
    str_path = str(path)
    nodes = result["nodes"]
    edges = result["edges"]
    seen_ids = {n["id"] for n in nodes}
    file_nid = _make_id(stem)

    def _get_docstring(body_node) -> tuple[str, int] | None:
        if not body_node:
            return None
        for child in body_node.children:
            if child.type == "expression_statement":
                for sub in child.children:
                    if sub.type in ("string", "concatenated_string"):
                        text = source[sub.start_byte:sub.end_byte].decode("utf-8", errors="replace")
                        text = text.strip("\"'").strip('"""').strip("'''").strip()
                        if len(text) > 20:
                            return text, child.start_point[0] + 1
            break
        return None

    def _add_rationale(text: str, line: int, parent_nid: str) -> None:
        label = text[:80].replace("\n", " ").strip()
        rid = _make_id(stem, "rationale", str(line))
        if rid not in seen_ids:
            seen_ids.add(rid)
            nodes.append({"id": rid, "label": label, "file_type": "rationale",
                          "source_file": str_path, "source_location": f"L{line}"})
        edges.append({"source": rid, "target": parent_nid, "relation": "rationale_for",
                      "confidence": "EXTRACTED", "source_file": str_path,
                      "source_location": f"L{line}", "weight": 1.0})

    # Module-level docstring
    ds = _get_docstring(root)
    if ds:
        _add_rationale(ds[0], ds[1], file_nid)

    def walk_docstrings(node, parent_nid: str) -> None:
        t = node.type
        if t == "class_definition":
            name_node = node.child_by_field_name("name")
            body = node.child_by_field_name("body")
            if name_node and body:
                class_name = source[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                nid = _make_id(stem, class_name)
                ds = _get_docstring(body)
                if ds:
                    _add_rationale(ds[0], ds[1], nid)
                for child in body.children:
                    walk_docstrings(child, nid)
            return
        if t == "function_definition":
            name_node = node.child_by_field_name("name")
            body = node.child_by_field_name("body")
            if name_node and body:
                func_name = source[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                nid = _make_id(parent_nid, func_name) if parent_nid != file_nid else _make_id(stem, func_name)
                ds = _get_docstring(body)
                if ds:
                    _add_rationale(ds[0], ds[1], nid)
            return
        for child in node.children:
            walk_docstrings(child, parent_nid)

    walk_docstrings(root, file_nid)

    # Rationale comments
    source_text = source.decode("utf-8", errors="replace")
    for lineno, line_text in enumerate(source_text.splitlines(), start=1):
        stripped = line_text.strip()
        if any(stripped.startswith(p) for p in _RATIONALE_PREFIXES):
            _add_rationale(stripped, lineno, file_nid)


def resolve_cross_file_imports(per_file: list[dict], paths: list[Path]) -> list[dict]:
    """Turn file-level Python imports into class-level INFERRED edges.

    Two-pass: build global name→node_id map, then for each `from .X import A`
    emit direct INFERRED edges from local classes to the imported entity.
    """
    try:
        import tree_sitter_python as tspython
        from tree_sitter import Language, Parser
    except ImportError:
        return []

    language = Language(tspython.language())
    parser = Parser(language)

    # Pass 1: stem → {ClassName: node_id}
    # Only index real code entities (functions/classes), not rationale/docstring nodes
    stem_to_entities: dict[str, dict[str, str]] = {}
    for file_result in per_file:
        for node in file_result.get("nodes", []):
            src = node.get("source_file", "")
            if not src:
                continue
            stem = Path(src).stem
            label = node.get("label", "")
            nid = node.get("id", "")
            # Skip rationale nodes and sentence-like labels (docstring descriptions)
            if node.get("file_type") == "rationale":
                continue
            if len(label.split()) > 5:
                continue
            if label and not label.endswith((")", ".py")) and "_" not in label[:1]:
                stem_to_entities.setdefault(stem, {})[label] = nid

    new_edges: list[dict] = []

    for file_result, path in zip(per_file, paths):
        stem = path.stem
        str_path = str(path)
        local_classes = [
            n["id"] for n in file_result.get("nodes", [])
            if n.get("source_file") == str_path
            and not n["label"].endswith((")", ".py"))
            and n["id"] != _make_id(stem)
            # Skip rationale/docstring nodes — they are not real code entities
            and n.get("file_type") != "rationale"
            # Skip nodes whose label looks like a sentence (docstring descriptions)
            and len(n["label"].split()) <= 5
        ]
        if not local_classes:
            continue
        try:
            source = path.read_bytes()
            tree = parser.parse(source)
        except Exception:
            continue

        def walk_imports(node) -> None:
            if node.type == "import_from_statement":
                target_stem: str | None = None
                for child in node.children:
                    if child.type == "relative_import":
                        for sub in child.children:
                            if sub.type == "dotted_name":
                                raw = source[sub.start_byte:sub.end_byte].decode("utf-8", errors="replace")
                                target_stem = raw.split(".")[-1]
                                break
                        break
                    if child.type == "dotted_name" and target_stem is None:
                        raw = source[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                        target_stem = raw.split(".")[-1]
                if not target_stem or target_stem not in stem_to_entities:
                    return
                imported_names: list[str] = []
                past_import_kw = False
                for child in node.children:
                    if child.type == "import":
                        past_import_kw = True
                        continue
                    if not past_import_kw:
                        continue
                    if child.type == "dotted_name":
                        imported_names.append(
                            source[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
                        )
                    elif child.type == "aliased_import":
                        name_node = child.child_by_field_name("name")
                        if name_node:
                            imported_names.append(
                                source[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                            )
                line = node.start_point[0] + 1
                for name in imported_names:
                    tgt_nid = stem_to_entities[target_stem].get(name)
                    if tgt_nid:
                        for src_class_nid in local_classes:
                            new_edges.append({
                                "source": src_class_nid, "target": tgt_nid,
                                "relation": "uses", "confidence": "INFERRED",
                                "source_file": str_path,
                                "source_location": f"L{line}", "weight": 0.8,
                            })
            for child in node.children:
                walk_imports(child)

        walk_imports(tree.root_node)

    return new_edges
