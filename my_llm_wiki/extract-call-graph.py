# call-graph inference — resolves function call edges within a parsed AST
from __future__ import annotations

import importlib

_core = importlib.import_module("my_llm_wiki.extract-core")
_read_text = _core._read_text


def build_label_index(nodes: list[dict]) -> dict[str, str]:
    """Build a map of normalised label → node ID for call resolution."""
    label_to_nid: dict[str, str] = {}
    for n in nodes:
        raw = n["label"]
        normalised = raw.strip("()").lstrip(".")
        label_to_nid[normalised.lower()] = n["id"]
    return label_to_nid


def walk_calls(
    node,
    caller_nid: str,
    config,
    source: bytes,
    label_to_nid: dict[str, str],
    seen_pairs: set[tuple[str, str]],
    edges: list[dict],
    str_path: str,
) -> None:
    """Recursively walk a function body resolving call expressions to known node IDs."""
    if node.type in config.function_boundary_types:
        return

    if node.type in config.call_types:
        callee_name: str | None = None

        if config.ts_module == "tree_sitter_swift":
            first = node.children[0] if node.children else None
            if first:
                if first.type == "simple_identifier":
                    callee_name = _read_text(first, source)
                elif first.type == "navigation_expression":
                    for child in first.children:
                        if child.type == "navigation_suffix":
                            for sc in child.children:
                                if sc.type == "simple_identifier":
                                    callee_name = _read_text(sc, source)

        elif config.ts_module == "tree_sitter_kotlin":
            first = node.children[0] if node.children else None
            if first:
                if first.type == "simple_identifier":
                    callee_name = _read_text(first, source)
                elif first.type == "navigation_expression":
                    for child in reversed(first.children):
                        if child.type == "simple_identifier":
                            callee_name = _read_text(child, source)
                            break

        elif config.ts_module == "tree_sitter_scala":
            first = node.children[0] if node.children else None
            if first:
                if first.type == "identifier":
                    callee_name = _read_text(first, source)
                elif first.type == "field_expression":
                    field = first.child_by_field_name("field")
                    if field:
                        callee_name = _read_text(field, source)
                    else:
                        for child in reversed(first.children):
                            if child.type == "identifier":
                                callee_name = _read_text(child, source)
                                break

        elif config.ts_module == "tree_sitter_c_sharp" and node.type == "invocation_expression":
            name_node = node.child_by_field_name("name")
            if name_node:
                callee_name = _read_text(name_node, source)
            else:
                for child in node.children:
                    if child.is_named:
                        raw = _read_text(child, source)
                        callee_name = raw.split(".")[-1] if "." in raw else raw
                        break

        elif config.ts_module == "tree_sitter_php":
            if node.type == "function_call_expression":
                func_node = node.child_by_field_name("function")
                if func_node:
                    callee_name = _read_text(func_node, source)
            else:
                name_node = node.child_by_field_name("name")
                if name_node:
                    callee_name = _read_text(name_node, source)

        elif config.ts_module == "tree_sitter_cpp":
            func_node = (
                node.child_by_field_name(config.call_function_field)
                if config.call_function_field else None
            )
            if func_node:
                if func_node.type == "identifier":
                    callee_name = _read_text(func_node, source)
                elif func_node.type in ("field_expression", "qualified_identifier"):
                    name = (
                        func_node.child_by_field_name("field")
                        or func_node.child_by_field_name("name")
                    )
                    if name:
                        callee_name = _read_text(name, source)

        else:
            # Generic: get callee from call_function_field
            func_node = (
                node.child_by_field_name(config.call_function_field)
                if config.call_function_field else None
            )
            if func_node:
                if func_node.type == "identifier":
                    callee_name = _read_text(func_node, source)
                elif func_node.type in config.call_accessor_node_types:
                    if config.call_accessor_field:
                        attr = func_node.child_by_field_name(config.call_accessor_field)
                        if attr:
                            callee_name = _read_text(attr, source)
                else:
                    callee_name = _read_text(func_node, source)

        if callee_name:
            tgt_nid = label_to_nid.get(callee_name.lower())
            if tgt_nid and tgt_nid != caller_nid:
                pair = (caller_nid, tgt_nid)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    line = node.start_point[0] + 1
                    edges.append({
                        "source": caller_nid,
                        "target": tgt_nid,
                        "relation": "calls",
                        "confidence": "INFERRED",
                        "source_file": str_path,
                        "source_location": f"L{line}",
                        "weight": 0.8,
                    })

    for child in node.children:
        walk_calls(child, caller_nid, config, source, label_to_nid, seen_pairs, edges, str_path)
