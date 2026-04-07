# shared types and helper functions for AST extraction
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable


def _make_id(*parts: str) -> str:
    """Build a stable node ID from one or more name parts."""
    combined = "_".join(p.strip("_.") for p in parts if p)
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", combined)
    return cleaned.strip("_").lower()


def _read_text(node, source: bytes) -> str:
    """Decode a tree-sitter node's byte span from source."""
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _resolve_name(node, source: bytes, config: "LanguageConfig") -> str | None:
    """Get the name from a node using config.name_field, falling back to child types."""
    if config.resolve_function_name_fn is not None:
        # For C/C++ where the name is inside a declarator — caller handles separately
        return None
    n = node.child_by_field_name(config.name_field)
    if n:
        return _read_text(n, source)
    for child in node.children:
        if child.type in config.name_fallback_child_types:
            return _read_text(child, source)
    return None


def _find_body(node, config: "LanguageConfig"):
    """Find the body node using config.body_field, falling back to child types."""
    b = node.child_by_field_name(config.body_field)
    if b:
        return b
    for child in node.children:
        if child.type in config.body_fallback_child_types:
            return child
    return None


@dataclass
class LanguageConfig:
    ts_module: str                                    # e.g. "tree_sitter_python"
    ts_language_fn: str = "language"                  # attr to call: e.g. tslang.language()

    class_types: frozenset = frozenset()
    function_types: frozenset = frozenset()
    import_types: frozenset = frozenset()
    call_types: frozenset = frozenset()

    # Name extraction
    name_field: str = "name"
    name_fallback_child_types: tuple = ()

    # Body detection
    body_field: str = "body"
    body_fallback_child_types: tuple = ()             # e.g. ("declaration_list",)

    # Call name extraction
    call_function_field: str = "function"             # field on call node for callee
    call_accessor_node_types: frozenset = frozenset() # member/attribute nodes
    call_accessor_field: str = "attribute"            # field on accessor for method name

    # Stop recursion at these types in walk_calls
    function_boundary_types: frozenset = frozenset()

    # Import handler: called for import nodes instead of generic handling
    import_handler: Callable | None = None

    # Optional custom name resolver for functions (C, C++ declarator unwrapping)
    resolve_function_name_fn: Callable | None = None

    # Extra label formatting: if True, functions get "name()" label
    function_label_parens: bool = True

    # Extra walk hook called after generic dispatch (JS arrow functions, C# namespaces, etc.)
    extra_walk_fn: Callable | None = None
