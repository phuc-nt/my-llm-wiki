# per-language import edge handlers — called by the generic AST walker for import nodes
from __future__ import annotations

import importlib

_core = importlib.import_module("my_llm_wiki.extract-core")
_make_id = _core._make_id
_read_text = _core._read_text


def _import_python(node, source: bytes, file_nid: str, stem: str, edges: list, str_path: str) -> None:
    t = node.type
    if t == "import_statement":
        for child in node.children:
            if child.type in ("dotted_name", "aliased_import"):
                raw = _read_text(child, source)
                module_name = raw.split(" as ")[0].strip().lstrip(".")
                tgt_nid = _make_id(module_name)
                edges.append({
                    "source": file_nid, "target": tgt_nid, "relation": "imports",
                    "confidence": "EXTRACTED", "source_file": str_path,
                    "source_location": f"L{node.start_point[0] + 1}", "weight": 1.0,
                })
    elif t == "import_from_statement":
        module_node = node.child_by_field_name("module_name")
        if module_node:
            raw = _read_text(module_node, source).lstrip(".")
            tgt_nid = _make_id(raw)
            edges.append({
                "source": file_nid, "target": tgt_nid, "relation": "imports_from",
                "confidence": "EXTRACTED", "source_file": str_path,
                "source_location": f"L{node.start_point[0] + 1}", "weight": 1.0,
            })


def _import_js(node, source: bytes, file_nid: str, stem: str, edges: list, str_path: str) -> None:
    for child in node.children:
        if child.type == "string":
            raw = _read_text(child, source).strip("'\"` ")
            module_name = raw.lstrip("./").split("/")[-1]
            if module_name:
                tgt_nid = _make_id(module_name)
                edges.append({
                    "source": file_nid, "target": tgt_nid, "relation": "imports_from",
                    "confidence": "EXTRACTED", "source_file": str_path,
                    "source_location": f"L{node.start_point[0] + 1}", "weight": 1.0,
                })
            break


def _import_java(node, source: bytes, file_nid: str, stem: str, edges: list, str_path: str) -> None:
    def _walk_scoped(n) -> str:
        parts: list[str] = []
        cur = n
        while cur:
            if cur.type == "scoped_identifier":
                name_node = cur.child_by_field_name("name")
                if name_node:
                    parts.append(_read_text(name_node, source))
                cur = cur.child_by_field_name("scope")
            elif cur.type == "identifier":
                parts.append(_read_text(cur, source))
                break
            else:
                break
        parts.reverse()
        return ".".join(parts)

    for child in node.children:
        if child.type in ("scoped_identifier", "identifier"):
            path_str = _walk_scoped(child)
            module_name = path_str.split(".")[-1].strip("*").strip(".") or (
                path_str.split(".")[-2] if len(path_str.split(".")) > 1 else path_str
            )
            if module_name:
                tgt_nid = _make_id(module_name)
                edges.append({
                    "source": file_nid, "target": tgt_nid, "relation": "imports",
                    "confidence": "EXTRACTED", "source_file": str_path,
                    "source_location": f"L{node.start_point[0] + 1}", "weight": 1.0,
                })
            break


def _import_c(node, source: bytes, file_nid: str, stem: str, edges: list, str_path: str) -> None:
    for child in node.children:
        if child.type in ("string_literal", "system_lib_string", "string"):
            raw = _read_text(child, source).strip('"<> ')
            module_name = raw.split("/")[-1].split(".")[0]
            if module_name:
                tgt_nid = _make_id(module_name)
                edges.append({
                    "source": file_nid, "target": tgt_nid, "relation": "imports",
                    "confidence": "EXTRACTED", "source_file": str_path,
                    "source_location": f"L{node.start_point[0] + 1}", "weight": 1.0,
                })
            break


def _import_csharp(node, source: bytes, file_nid: str, stem: str, edges: list, str_path: str) -> None:
    for child in node.children:
        if child.type in ("qualified_name", "identifier", "name_equals"):
            raw = _read_text(child, source)
            module_name = raw.split(".")[-1].strip()
            if module_name:
                tgt_nid = _make_id(module_name)
                edges.append({
                    "source": file_nid, "target": tgt_nid, "relation": "imports",
                    "confidence": "EXTRACTED", "source_file": str_path,
                    "source_location": f"L{node.start_point[0] + 1}", "weight": 1.0,
                })
            break


def _import_kotlin(node, source: bytes, file_nid: str, stem: str, edges: list, str_path: str) -> None:
    path_node = node.child_by_field_name("path")
    if path_node:
        raw = _read_text(path_node, source)
        module_name = raw.split(".")[-1].strip()
        if module_name:
            tgt_nid = _make_id(module_name)
            edges.append({
                "source": file_nid, "target": tgt_nid, "relation": "imports",
                "confidence": "EXTRACTED", "source_file": str_path,
                "source_location": f"L{node.start_point[0] + 1}", "weight": 1.0,
            })
        return
    # Fallback: find identifier child
    for child in node.children:
        if child.type == "identifier":
            raw = _read_text(child, source)
            tgt_nid = _make_id(raw)
            edges.append({
                "source": file_nid, "target": tgt_nid, "relation": "imports",
                "confidence": "EXTRACTED", "source_file": str_path,
                "source_location": f"L{node.start_point[0] + 1}", "weight": 1.0,
            })
            break


def _import_scala(node, source: bytes, file_nid: str, stem: str, edges: list, str_path: str) -> None:
    for child in node.children:
        if child.type in ("stable_id", "identifier"):
            raw = _read_text(child, source)
            module_name = raw.split(".")[-1].strip("{} ")
            if module_name and module_name != "_":
                tgt_nid = _make_id(module_name)
                edges.append({
                    "source": file_nid, "target": tgt_nid, "relation": "imports",
                    "confidence": "EXTRACTED", "source_file": str_path,
                    "source_location": f"L{node.start_point[0] + 1}", "weight": 1.0,
                })
            break


def _import_php(node, source: bytes, file_nid: str, stem: str, edges: list, str_path: str) -> None:
    for child in node.children:
        if child.type in ("qualified_name", "name", "identifier"):
            raw = _read_text(child, source)
            module_name = raw.split("\\")[-1].strip()
            if module_name:
                tgt_nid = _make_id(module_name)
                edges.append({
                    "source": file_nid, "target": tgt_nid, "relation": "imports",
                    "confidence": "EXTRACTED", "source_file": str_path,
                    "source_location": f"L{node.start_point[0] + 1}", "weight": 1.0,
                })
            break


def _import_lua(node, source: bytes, file_nid: str, stem: str, edges: list, str_path: str) -> None:
    """Extract require('module') from Lua variable_declaration nodes."""
    import re as _re
    text = _read_text(node, source)
    m = _re.search(r"""require\s*[\('"]\s*['"]?([^'")\s]+)""", text)
    if m:
        module_name = m.group(1).split(".")[-1]
        if module_name:
            edges.append({
                "source": file_nid, "target": module_name, "relation": "imports",
                "confidence": "EXTRACTED", "confidence_score": 1.0,
                "source_file": str_path,
                "source_location": str(node.start_point[0] + 1), "weight": 1.0,
            })


def _import_swift(node, source: bytes, file_nid: str, stem: str, edges: list, str_path: str) -> None:
    for child in node.children:
        if child.type == "identifier":
            raw = _read_text(child, source)
            tgt_nid = _make_id(raw)
            edges.append({
                "source": file_nid, "target": tgt_nid, "relation": "imports",
                "confidence": "EXTRACTED", "source_file": str_path,
                "source_location": f"L{node.start_point[0] + 1}", "weight": 1.0,
            })
            break
