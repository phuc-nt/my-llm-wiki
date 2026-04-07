# custom AST extractors for Go, Rust, Zig, PowerShell, Elixir
# these languages don't use _extract_generic — each has its own walk logic
from __future__ import annotations

from pathlib import Path
from typing import Any
import importlib

_core = importlib.import_module("my_llm_wiki.extract-core")
_make_id = _core._make_id
_read_text = _core._read_text


def _make_helpers(stem: str, str_path: str):
    """Return (nodes, edges, seen_ids, function_bodies, add_node, add_edge, file_nid)."""
    nodes: list[dict] = []
    edges: list[dict] = []
    seen_ids: set[str] = set()
    function_bodies: list[tuple[str, Any]] = []

    def add_node(nid: str, label: str, line: int) -> None:
        if nid not in seen_ids:
            seen_ids.add(nid)
            nodes.append({"id": nid, "label": label, "file_type": "code",
                          "source_file": str_path, "source_location": f"L{line}"})

    def add_edge(src: str, tgt: str, relation: str, line: int,
                 confidence: str = "EXTRACTED", weight: float = 1.0) -> None:
        edges.append({"source": src, "target": tgt, "relation": relation,
                      "confidence": confidence, "source_file": str_path,
                      "source_location": f"L{line}", "weight": weight})

    file_nid = _make_id(stem)
    add_node(file_nid, f"{stem}.{str_path.rsplit('.', 1)[-1]}", 1)
    return nodes, edges, seen_ids, function_bodies, add_node, add_edge, file_nid


def _clean(nodes, edges, seen_ids, import_relations=("imports", "imports_from")) -> list[dict]:
    return [e for e in edges if e["source"] in seen_ids
            and (e["target"] in seen_ids or e["relation"] in import_relations)]


# ── Go ────────────────────────────────────────────────────────────────────────

def extract_go(path: Path) -> dict:
    """Extract functions, methods, type declarations, and imports from a .go file."""
    try:
        import tree_sitter_go as tsgo
        from tree_sitter import Language, Parser
    except ImportError:
        return {"nodes": [], "edges": [], "error": "tree-sitter-go not installed"}
    try:
        language = Language(tsgo.language())
        parser = Parser(language)
        source = path.read_bytes()
        root = parser.parse(source).root_node
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}

    stem = path.stem
    str_path = str(path)
    nodes, edges, seen_ids, function_bodies, add_node, add_edge, file_nid = _make_helpers(stem, str_path)
    # overwrite file node with correct label
    nodes[0]["label"] = path.name

    def walk(node) -> None:
        t = node.type
        if t == "function_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                func_name = _read_text(name_node, source)
                line = node.start_point[0] + 1
                func_nid = _make_id(stem, func_name)
                add_node(func_nid, f"{func_name}()", line)
                add_edge(file_nid, func_nid, "contains", line)
                body = node.child_by_field_name("body")
                if body:
                    function_bodies.append((func_nid, body))
            return
        if t == "method_declaration":
            receiver = node.child_by_field_name("receiver")
            receiver_type: str | None = None
            if receiver:
                for param in receiver.children:
                    if param.type == "parameter_declaration":
                        type_node = param.child_by_field_name("type")
                        if type_node:
                            receiver_type = _read_text(type_node, source).lstrip("*").strip()
                        break
            name_node = node.child_by_field_name("name")
            if name_node:
                method_name = _read_text(name_node, source)
                line = node.start_point[0] + 1
                if receiver_type:
                    parent_nid = _make_id(stem, receiver_type)
                    add_node(parent_nid, receiver_type, line)
                    method_nid = _make_id(parent_nid, method_name)
                    add_node(method_nid, f".{method_name}()", line)
                    add_edge(parent_nid, method_nid, "method", line)
                else:
                    method_nid = _make_id(stem, method_name)
                    add_node(method_nid, f"{method_name}()", line)
                    add_edge(file_nid, method_nid, "contains", line)
                body = node.child_by_field_name("body")
                if body:
                    function_bodies.append((method_nid, body))
            return
        if t == "type_declaration":
            for child in node.children:
                if child.type == "type_spec":
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        type_name = _read_text(name_node, source)
                        line = child.start_point[0] + 1
                        type_nid = _make_id(stem, type_name)
                        add_node(type_nid, type_name, line)
                        add_edge(file_nid, type_nid, "contains", line)
            return
        if t == "import_declaration":
            for child in node.children:
                if child.type == "import_spec_list":
                    for spec in child.children:
                        if spec.type == "import_spec":
                            path_node = spec.child_by_field_name("path")
                            if path_node:
                                raw = _read_text(path_node, source).strip('"')
                                tgt_nid = _make_id(raw.split("/")[-1])
                                add_edge(file_nid, tgt_nid, "imports_from", spec.start_point[0] + 1)
                elif child.type == "import_spec":
                    path_node = child.child_by_field_name("path")
                    if path_node:
                        raw = _read_text(path_node, source).strip('"')
                        tgt_nid = _make_id(raw.split("/")[-1])
                        add_edge(file_nid, tgt_nid, "imports_from", child.start_point[0] + 1)
            return
        for child in node.children:
            walk(child)

    walk(root)

    label_to_nid = {n["label"].strip("()").lstrip(".").lower(): n["id"] for n in nodes}
    seen_call_pairs: set[tuple[str, str]] = set()

    def walk_calls_go(node, caller_nid: str) -> None:
        if node.type in ("function_declaration", "method_declaration"):
            return
        if node.type == "call_expression":
            func_node = node.child_by_field_name("function")
            callee_name: str | None = None
            if func_node:
                if func_node.type == "identifier":
                    callee_name = _read_text(func_node, source)
                elif func_node.type == "selector_expression":
                    field = func_node.child_by_field_name("field")
                    if field:
                        callee_name = _read_text(field, source)
            if callee_name:
                tgt_nid = label_to_nid.get(callee_name.lower())
                if tgt_nid and tgt_nid != caller_nid:
                    pair = (caller_nid, tgt_nid)
                    if pair not in seen_call_pairs:
                        seen_call_pairs.add(pair)
                        edges.append({"source": caller_nid, "target": tgt_nid,
                                      "relation": "calls", "confidence": "INFERRED",
                                      "source_file": str_path,
                                      "source_location": f"L{node.start_point[0] + 1}",
                                      "weight": 0.8})
        for child in node.children:
            walk_calls_go(child, caller_nid)

    for caller_nid, body_node in function_bodies:
        walk_calls_go(body_node, caller_nid)

    return {"nodes": nodes, "edges": _clean(nodes, edges, seen_ids)}


# ── Rust ──────────────────────────────────────────────────────────────────────

def extract_rust(path: Path) -> dict:
    """Extract functions, structs, enums, traits, impl methods, and use declarations from a .rs file."""
    try:
        import tree_sitter_rust as tsrust
        from tree_sitter import Language, Parser
    except ImportError:
        return {"nodes": [], "edges": [], "error": "tree-sitter-rust not installed"}
    try:
        language = Language(tsrust.language())
        parser = Parser(language)
        source = path.read_bytes()
        root = parser.parse(source).root_node
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}

    stem = path.stem
    str_path = str(path)
    nodes, edges, seen_ids, function_bodies, add_node, add_edge, file_nid = _make_helpers(stem, str_path)
    nodes[0]["label"] = path.name

    def walk(node, parent_impl_nid: str | None = None) -> None:
        t = node.type
        if t == "function_item":
            name_node = node.child_by_field_name("name")
            if name_node:
                func_name = _read_text(name_node, source)
                line = node.start_point[0] + 1
                if parent_impl_nid:
                    func_nid = _make_id(parent_impl_nid, func_name)
                    add_node(func_nid, f".{func_name}()", line)
                    add_edge(parent_impl_nid, func_nid, "method", line)
                else:
                    func_nid = _make_id(stem, func_name)
                    add_node(func_nid, f"{func_name}()", line)
                    add_edge(file_nid, func_nid, "contains", line)
                body = node.child_by_field_name("body")
                if body:
                    function_bodies.append((func_nid, body))
            return
        if t in ("struct_item", "enum_item", "trait_item"):
            name_node = node.child_by_field_name("name")
            if name_node:
                item_name = _read_text(name_node, source)
                line = node.start_point[0] + 1
                item_nid = _make_id(stem, item_name)
                add_node(item_nid, item_name, line)
                add_edge(file_nid, item_nid, "contains", line)
            return
        if t == "impl_item":
            type_node = node.child_by_field_name("type")
            impl_nid: str | None = None
            if type_node:
                type_name = _read_text(type_node, source).strip()
                impl_nid = _make_id(stem, type_name)
                add_node(impl_nid, type_name, node.start_point[0] + 1)
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    walk(child, parent_impl_nid=impl_nid)
            return
        if t == "use_declaration":
            arg = node.child_by_field_name("argument")
            if arg:
                raw = _read_text(arg, source)
                clean = raw.split("{")[0].rstrip(":").rstrip("*").rstrip(":")
                module_name = clean.split("::")[-1].strip()
                if module_name:
                    add_edge(file_nid, _make_id(module_name), "imports_from", node.start_point[0] + 1)
            return
        for child in node.children:
            walk(child, parent_impl_nid=None)

    walk(root)

    label_to_nid = {n["label"].strip("()").lstrip(".").lower(): n["id"] for n in nodes}
    seen_call_pairs: set[tuple[str, str]] = set()

    def walk_calls_rust(node, caller_nid: str) -> None:
        if node.type == "function_item":
            return
        if node.type == "call_expression":
            func_node = node.child_by_field_name("function")
            callee_name: str | None = None
            if func_node:
                if func_node.type == "identifier":
                    callee_name = _read_text(func_node, source)
                elif func_node.type == "field_expression":
                    field = func_node.child_by_field_name("field")
                    if field:
                        callee_name = _read_text(field, source)
                elif func_node.type == "scoped_identifier":
                    name = func_node.child_by_field_name("name")
                    if name:
                        callee_name = _read_text(name, source)
            if callee_name:
                tgt_nid = label_to_nid.get(callee_name.lower())
                if tgt_nid and tgt_nid != caller_nid:
                    pair = (caller_nid, tgt_nid)
                    if pair not in seen_call_pairs:
                        seen_call_pairs.add(pair)
                        edges.append({"source": caller_nid, "target": tgt_nid,
                                      "relation": "calls", "confidence": "INFERRED",
                                      "source_file": str_path,
                                      "source_location": f"L{node.start_point[0] + 1}",
                                      "weight": 0.8})
        for child in node.children:
            walk_calls_rust(child, caller_nid)

    for caller_nid, body_node in function_bodies:
        walk_calls_rust(body_node, caller_nid)

    return {"nodes": nodes, "edges": _clean(nodes, edges, seen_ids)}
