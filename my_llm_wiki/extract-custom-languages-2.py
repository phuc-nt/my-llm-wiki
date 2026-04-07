# custom AST extractors for Zig and PowerShell
from __future__ import annotations

from pathlib import Path
from typing import Any
import importlib

_core = importlib.import_module("my_llm_wiki.extract-core")
_make_id = _core._make_id
_read_text = _core._read_text

_custom = importlib.import_module("my_llm_wiki.extract-custom-languages")
_make_helpers = _custom._make_helpers
_clean = _custom._clean


# ── Zig ───────────────────────────────────────────────────────────────────────

def extract_zig(path: Path) -> dict:
    """Extract functions, structs, enums, unions, and imports from a .zig file."""
    try:
        import tree_sitter_zig as tszig
        from tree_sitter import Language, Parser
    except ImportError:
        return {"nodes": [], "edges": [], "error": "tree_sitter_zig not installed"}
    try:
        language = Language(tszig.language())
        parser = Parser(language)
        source = path.read_bytes()
        root = parser.parse(source).root_node
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}

    stem = path.stem
    str_path = str(path)
    nodes, edges, seen_ids, function_bodies, add_node, add_edge, file_nid = _make_helpers(stem, str_path)
    nodes[0]["label"] = path.name

    def _extract_import(node) -> None:
        for child in node.children:
            if child.type == "builtin_function":
                bi = None
                args = None
                for c in child.children:
                    if c.type == "builtin_identifier":
                        bi = _read_text(c, source)
                    elif c.type == "arguments":
                        args = c
                if bi in ("@import", "@cImport") and args:
                    for arg in args.children:
                        if arg.type in ("string_literal", "string"):
                            raw = _read_text(arg, source).strip('"')
                            module_name = raw.split("/")[-1].split(".")[0]
                            if module_name:
                                add_edge(file_nid, _make_id(module_name), "imports_from",
                                         node.start_point[0] + 1)
                            return
            elif child.type == "field_expression":
                _extract_import(child)
                return

    def walk(node, parent_struct_nid: str | None = None) -> None:
        t = node.type
        if t == "function_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                func_name = _read_text(name_node, source)
                line = node.start_point[0] + 1
                if parent_struct_nid:
                    func_nid = _make_id(parent_struct_nid, func_name)
                    add_node(func_nid, f".{func_name}()", line)
                    add_edge(parent_struct_nid, func_nid, "method", line)
                else:
                    func_nid = _make_id(stem, func_name)
                    add_node(func_nid, f"{func_name}()", line)
                    add_edge(file_nid, func_nid, "contains", line)
                body = node.child_by_field_name("body")
                if body:
                    function_bodies.append((func_nid, body))
            return
        if t == "variable_declaration":
            name_node = None
            value_node = None
            for child in node.children:
                if child.type == "identifier":
                    name_node = child
                elif child.type in ("struct_declaration", "enum_declaration",
                                    "union_declaration", "builtin_function",
                                    "field_expression"):
                    value_node = child
            if value_node and value_node.type == "struct_declaration":
                if name_node:
                    struct_name = _read_text(name_node, source)
                    line = node.start_point[0] + 1
                    struct_nid = _make_id(stem, struct_name)
                    add_node(struct_nid, struct_name, line)
                    add_edge(file_nid, struct_nid, "contains", line)
                    for child in value_node.children:
                        walk(child, parent_struct_nid=struct_nid)
                return
            if value_node and value_node.type in ("enum_declaration", "union_declaration"):
                if name_node:
                    type_name = _read_text(name_node, source)
                    line = node.start_point[0] + 1
                    type_nid = _make_id(stem, type_name)
                    add_node(type_nid, type_name, line)
                    add_edge(file_nid, type_nid, "contains", line)
                return
            if value_node and value_node.type in ("builtin_function", "field_expression"):
                _extract_import(node)
            return
        for child in node.children:
            walk(child, parent_struct_nid)

    walk(root)

    seen_call_pairs: set[tuple[str, str]] = set()

    def walk_calls_zig(node, caller_nid: str) -> None:
        if node.type == "function_declaration":
            return
        if node.type == "call_expression":
            fn = node.child_by_field_name("function")
            if fn:
                callee = _read_text(fn, source).split(".")[-1]
                tgt_nid = next(
                    (n["id"] for n in nodes if n["label"] in (f"{callee}()", f".{callee}()")),
                    None,
                )
                if tgt_nid and tgt_nid != caller_nid:
                    pair = (caller_nid, tgt_nid)
                    if pair not in seen_call_pairs:
                        seen_call_pairs.add(pair)
                        add_edge(caller_nid, tgt_nid, "calls", node.start_point[0] + 1,
                                 confidence="INFERRED", weight=0.8)
        for child in node.children:
            walk_calls_zig(child, caller_nid)

    for caller_nid, body_node in function_bodies:
        walk_calls_zig(body_node, caller_nid)

    return {"nodes": nodes, "edges": _clean(nodes, edges, seen_ids)}


# ── PowerShell ────────────────────────────────────────────────────────────────

def extract_powershell(path: Path) -> dict:
    """Extract functions, classes, methods, and using statements from a .ps1 file."""
    try:
        import tree_sitter_powershell as tsps
        from tree_sitter import Language, Parser
    except ImportError:
        return {"nodes": [], "edges": [], "error": "tree_sitter_powershell not installed"}
    try:
        language = Language(tsps.language())
        parser = Parser(language)
        source = path.read_bytes()
        root = parser.parse(source).root_node
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}

    stem = path.stem
    str_path = str(path)
    nodes, edges, seen_ids, function_bodies, add_node, add_edge, file_nid = _make_helpers(stem, str_path)
    nodes[0]["label"] = path.name

    _PS_SKIP = frozenset({
        "using", "return", "if", "else", "elseif", "foreach", "for",
        "while", "do", "switch", "try", "catch", "finally", "throw",
        "break", "continue", "exit", "param", "begin", "process", "end",
    })

    def _find_script_block_body(node):
        for child in node.children:
            if child.type == "script_block":
                for sc in child.children:
                    if sc.type == "script_block_body":
                        return sc
                return child
        return None

    def walk(node, parent_class_nid: str | None = None) -> None:
        t = node.type
        if t == "function_statement":
            name_node = next((c for c in node.children if c.type == "function_name"), None)
            if name_node:
                func_name = _read_text(name_node, source)
                line = node.start_point[0] + 1
                func_nid = _make_id(stem, func_name)
                add_node(func_nid, f"{func_name}()", line)
                add_edge(file_nid, func_nid, "contains", line)
                body = _find_script_block_body(node)
                if body:
                    function_bodies.append((func_nid, body))
            return
        if t == "class_statement":
            name_node = next((c for c in node.children if c.type == "simple_name"), None)
            if name_node:
                class_name = _read_text(name_node, source)
                line = node.start_point[0] + 1
                class_nid = _make_id(stem, class_name)
                add_node(class_nid, class_name, line)
                add_edge(file_nid, class_nid, "contains", line)
                for child in node.children:
                    walk(child, parent_class_nid=class_nid)
            return
        if t == "class_method_definition":
            name_node = next((c for c in node.children if c.type == "simple_name"), None)
            if name_node:
                method_name = _read_text(name_node, source)
                line = node.start_point[0] + 1
                if parent_class_nid:
                    method_nid = _make_id(parent_class_nid, method_name)
                    add_node(method_nid, f".{method_name}()", line)
                    add_edge(parent_class_nid, method_nid, "method", line)
                else:
                    method_nid = _make_id(stem, method_name)
                    add_node(method_nid, f"{method_name}()", line)
                    add_edge(file_nid, method_nid, "contains", line)
                body = _find_script_block_body(node)
                if body:
                    function_bodies.append((method_nid, body))
            return
        if t == "command":
            cmd_name_node = next((c for c in node.children if c.type == "command_name"), None)
            if cmd_name_node:
                cmd_text = _read_text(cmd_name_node, source).lower()
                if cmd_text == "using":
                    tokens = []
                    for child in node.children:
                        if child.type == "command_elements":
                            for el in child.children:
                                if el.type == "generic_token":
                                    tokens.append(_read_text(el, source))
                    module_tokens = [tok for tok in tokens
                                     if tok.lower() not in ("namespace", "module", "assembly")]
                    if module_tokens:
                        module_name = module_tokens[-1].split(".")[-1]
                        add_edge(file_nid, _make_id(module_name), "imports_from",
                                 node.start_point[0] + 1)
            return
        for child in node.children:
            walk(child, parent_class_nid)

    walk(root)

    label_to_nid = {n["label"].strip("()").lstrip(".").lower(): n["id"] for n in nodes}
    seen_call_pairs: set[tuple[str, str]] = set()

    def walk_calls_ps(node, caller_nid: str) -> None:
        if node.type in ("function_statement", "class_statement"):
            return
        if node.type == "command":
            cmd_name_node = next((c for c in node.children if c.type == "command_name"), None)
            if cmd_name_node:
                cmd_text = _read_text(cmd_name_node, source)
                if cmd_text.lower() not in _PS_SKIP:
                    tgt_nid = label_to_nid.get(cmd_text.lower())
                    if tgt_nid and tgt_nid != caller_nid:
                        pair = (caller_nid, tgt_nid)
                        if pair not in seen_call_pairs:
                            seen_call_pairs.add(pair)
                            add_edge(caller_nid, tgt_nid, "calls",
                                     node.start_point[0] + 1,
                                     confidence="INFERRED", weight=0.8)
        for child in node.children:
            walk_calls_ps(child, caller_nid)

    for caller_nid, body_node in function_bodies:
        walk_calls_ps(body_node, caller_nid)

    return {"nodes": nodes, "edges": _clean(nodes, edges, seen_ids)}
