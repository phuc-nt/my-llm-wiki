# LanguageConfig instances for all 16 supported languages + helper functions
from __future__ import annotations

import importlib

_core = importlib.import_module("my_llm_wiki.extract-core")
_handlers = importlib.import_module("my_llm_wiki.extract-import-handlers")

LanguageConfig = _core.LanguageConfig
_read_text = _core._read_text
_make_id = _core._make_id

_import_python = _handlers._import_python
_import_js = _handlers._import_js
_import_java = _handlers._import_java
_import_c = _handlers._import_c
_import_csharp = _handlers._import_csharp
_import_kotlin = _handlers._import_kotlin
_import_scala = _handlers._import_scala
_import_php = _handlers._import_php
_import_lua = _handlers._import_lua
_import_swift = _handlers._import_swift


# ── C/C++ function name helpers ───────────────────────────────────────────────

def _get_c_func_name(node, source: bytes) -> str | None:
    """Recursively unwrap declarator to find the innermost identifier (C)."""
    if node.type == "identifier":
        return _read_text(node, source)
    decl = node.child_by_field_name("declarator")
    if decl:
        return _get_c_func_name(decl, source)
    for child in node.children:
        if child.type == "identifier":
            return _read_text(child, source)
    return None


def _get_cpp_func_name(node, source: bytes) -> str | None:
    """Recursively unwrap declarator to find the innermost identifier (C++)."""
    if node.type == "identifier":
        return _read_text(node, source)
    if node.type == "qualified_identifier":
        name_node = node.child_by_field_name("name")
        if name_node:
            return _read_text(name_node, source)
    decl = node.child_by_field_name("declarator")
    if decl:
        return _get_cpp_func_name(decl, source)
    for child in node.children:
        if child.type == "identifier":
            return _read_text(child, source)
    return None


# ── JS/TS extra walk for arrow functions ──────────────────────────────────────

def _js_extra_walk(node, source: bytes, file_nid: str, stem: str, str_path: str,
                   nodes: list, edges: list, seen_ids: set, function_bodies: list,
                   parent_class_nid: str | None, add_node_fn, add_edge_fn) -> bool:
    """Handle lexical_declaration (arrow functions) for JS/TS. Returns True if handled."""
    if node.type == "lexical_declaration":
        for child in node.children:
            if child.type == "variable_declarator":
                value = child.child_by_field_name("value")
                if value and value.type == "arrow_function":
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        func_name = _read_text(name_node, source)
                        line = child.start_point[0] + 1
                        func_nid = _make_id(stem, func_name)
                        add_node_fn(func_nid, f"{func_name}()", line)
                        add_edge_fn(file_nid, func_nid, "contains", line)
                        body = value.child_by_field_name("body")
                        if body:
                            function_bodies.append((func_nid, body))
        return True
    return False


# ── C# extra walk for namespace declarations ──────────────────────────────────

def _csharp_extra_walk(node, source: bytes, file_nid: str, stem: str, str_path: str,
                       nodes: list, edges: list, seen_ids: set, function_bodies: list,
                       parent_class_nid: str | None, add_node_fn, add_edge_fn,
                       walk_fn) -> bool:
    """Handle namespace_declaration for C#. Returns True if handled."""
    if node.type == "namespace_declaration":
        name_node = node.child_by_field_name("name")
        if name_node:
            ns_name = _read_text(name_node, source)
            ns_nid = _make_id(stem, ns_name)
            line = node.start_point[0] + 1
            add_node_fn(ns_nid, ns_name, line)
            add_edge_fn(file_nid, ns_nid, "contains", line)
        body = node.child_by_field_name("body")
        if body:
            for child in body.children:
                walk_fn(child, parent_class_nid)
        return True
    return False


# ── Swift extra walk for enum cases ──────────────────────────────────────────

def _swift_extra_walk(node, source: bytes, file_nid: str, stem: str, str_path: str,
                      nodes: list, edges: list, seen_ids: set, function_bodies: list,
                      parent_class_nid: str | None, add_node_fn, add_edge_fn) -> bool:
    """Handle enum_entry for Swift. Returns True if handled."""
    if node.type == "enum_entry" and parent_class_nid:
        for child in node.children:
            if child.type == "simple_identifier":
                case_name = _read_text(child, source)
                case_nid = _make_id(parent_class_nid, case_name)
                line = node.start_point[0] + 1
                add_node_fn(case_nid, case_name, line)
                add_edge_fn(parent_class_nid, case_nid, "case_of", line)
        return True
    return False


# ── Language config instances ─────────────────────────────────────────────────

_PYTHON_CONFIG = LanguageConfig(
    ts_module="tree_sitter_python",
    class_types=frozenset({"class_definition"}),
    function_types=frozenset({"function_definition"}),
    import_types=frozenset({"import_statement", "import_from_statement"}),
    call_types=frozenset({"call"}),
    call_function_field="function",
    call_accessor_node_types=frozenset({"attribute"}),
    call_accessor_field="attribute",
    function_boundary_types=frozenset({"function_definition"}),
    import_handler=_import_python,
)

_JS_CONFIG = LanguageConfig(
    ts_module="tree_sitter_javascript",
    class_types=frozenset({"class_declaration"}),
    function_types=frozenset({"function_declaration", "method_definition"}),
    import_types=frozenset({"import_statement"}),
    call_types=frozenset({"call_expression"}),
    call_function_field="function",
    call_accessor_node_types=frozenset({"member_expression"}),
    call_accessor_field="property",
    function_boundary_types=frozenset({"function_declaration", "arrow_function", "method_definition"}),
    import_handler=_import_js,
)

_TS_CONFIG = LanguageConfig(
    ts_module="tree_sitter_typescript",
    ts_language_fn="language_typescript",
    class_types=frozenset({"class_declaration"}),
    function_types=frozenset({"function_declaration", "method_definition"}),
    import_types=frozenset({"import_statement"}),
    call_types=frozenset({"call_expression"}),
    call_function_field="function",
    call_accessor_node_types=frozenset({"member_expression"}),
    call_accessor_field="property",
    function_boundary_types=frozenset({"function_declaration", "arrow_function", "method_definition"}),
    import_handler=_import_js,
)

_JAVA_CONFIG = LanguageConfig(
    ts_module="tree_sitter_java",
    class_types=frozenset({"class_declaration", "interface_declaration"}),
    function_types=frozenset({"method_declaration", "constructor_declaration"}),
    import_types=frozenset({"import_declaration"}),
    call_types=frozenset({"method_invocation"}),
    call_function_field="name",
    call_accessor_node_types=frozenset(),
    function_boundary_types=frozenset({"method_declaration", "constructor_declaration"}),
    import_handler=_import_java,
)

_C_CONFIG = LanguageConfig(
    ts_module="tree_sitter_c",
    class_types=frozenset(),
    function_types=frozenset({"function_definition"}),
    import_types=frozenset({"preproc_include"}),
    call_types=frozenset({"call_expression"}),
    call_function_field="function",
    call_accessor_node_types=frozenset({"field_expression"}),
    call_accessor_field="field",
    function_boundary_types=frozenset({"function_definition"}),
    import_handler=_import_c,
    resolve_function_name_fn=_get_c_func_name,
)

_CPP_CONFIG = LanguageConfig(
    ts_module="tree_sitter_cpp",
    class_types=frozenset({"class_specifier"}),
    function_types=frozenset({"function_definition"}),
    import_types=frozenset({"preproc_include"}),
    call_types=frozenset({"call_expression"}),
    call_function_field="function",
    call_accessor_node_types=frozenset({"field_expression", "qualified_identifier"}),
    call_accessor_field="field",
    function_boundary_types=frozenset({"function_definition"}),
    import_handler=_import_c,
    resolve_function_name_fn=_get_cpp_func_name,
)

_RUBY_CONFIG = LanguageConfig(
    ts_module="tree_sitter_ruby",
    class_types=frozenset({"class"}),
    function_types=frozenset({"method", "singleton_method"}),
    import_types=frozenset(),
    call_types=frozenset({"call"}),
    call_function_field="method",
    call_accessor_node_types=frozenset(),
    name_fallback_child_types=("constant", "scope_resolution", "identifier"),
    body_fallback_child_types=("body_statement",),
    function_boundary_types=frozenset({"method", "singleton_method"}),
)

_CSHARP_CONFIG = LanguageConfig(
    ts_module="tree_sitter_c_sharp",
    class_types=frozenset({"class_declaration", "interface_declaration"}),
    function_types=frozenset({"method_declaration"}),
    import_types=frozenset({"using_directive"}),
    call_types=frozenset({"invocation_expression"}),
    call_function_field="function",
    call_accessor_node_types=frozenset({"member_access_expression"}),
    call_accessor_field="name",
    body_fallback_child_types=("declaration_list",),
    function_boundary_types=frozenset({"method_declaration"}),
    import_handler=_import_csharp,
)

_KOTLIN_CONFIG = LanguageConfig(
    ts_module="tree_sitter_kotlin",
    class_types=frozenset({"class_declaration", "object_declaration"}),
    function_types=frozenset({"function_declaration"}),
    import_types=frozenset({"import_header"}),
    call_types=frozenset({"call_expression"}),
    call_function_field="",
    call_accessor_node_types=frozenset({"navigation_expression"}),
    call_accessor_field="",
    name_fallback_child_types=("simple_identifier",),
    body_fallback_child_types=("function_body", "class_body"),
    function_boundary_types=frozenset({"function_declaration"}),
    import_handler=_import_kotlin,
)

_SCALA_CONFIG = LanguageConfig(
    ts_module="tree_sitter_scala",
    class_types=frozenset({"class_definition", "object_definition"}),
    function_types=frozenset({"function_definition"}),
    import_types=frozenset({"import_declaration"}),
    call_types=frozenset({"call_expression"}),
    call_function_field="",
    call_accessor_node_types=frozenset({"field_expression"}),
    call_accessor_field="field",
    name_fallback_child_types=("identifier",),
    body_fallback_child_types=("template_body",),
    function_boundary_types=frozenset({"function_definition"}),
    import_handler=_import_scala,
)

_PHP_CONFIG = LanguageConfig(
    ts_module="tree_sitter_php",
    ts_language_fn="language_php",
    class_types=frozenset({"class_declaration"}),
    function_types=frozenset({"function_definition", "method_declaration"}),
    import_types=frozenset({"namespace_use_clause"}),
    call_types=frozenset({"function_call_expression", "member_call_expression"}),
    call_function_field="function",
    call_accessor_node_types=frozenset({"member_call_expression"}),
    call_accessor_field="name",
    name_fallback_child_types=("name",),
    body_fallback_child_types=("declaration_list", "compound_statement"),
    function_boundary_types=frozenset({"function_definition", "method_declaration"}),
    import_handler=_import_php,
)

_LUA_CONFIG = LanguageConfig(
    ts_module="tree_sitter_lua",
    ts_language_fn="language",
    class_types=frozenset(),
    function_types=frozenset({"function_declaration"}),
    import_types=frozenset({"variable_declaration"}),
    call_types=frozenset({"function_call"}),
    call_function_field="name",
    call_accessor_node_types=frozenset({"method_index_expression"}),
    call_accessor_field="name",
    name_fallback_child_types=("identifier", "method_index_expression"),
    body_fallback_child_types=("block",),
    function_boundary_types=frozenset({"function_declaration"}),
    import_handler=_import_lua,
)

_SWIFT_CONFIG = LanguageConfig(
    ts_module="tree_sitter_swift",
    class_types=frozenset({"class_declaration", "protocol_declaration"}),
    function_types=frozenset({
        "function_declaration", "init_declaration",
        "deinit_declaration", "subscript_declaration",
    }),
    import_types=frozenset({"import_declaration"}),
    call_types=frozenset({"call_expression"}),
    call_function_field="",
    call_accessor_node_types=frozenset({"navigation_expression"}),
    call_accessor_field="",
    name_fallback_child_types=("simple_identifier", "type_identifier", "user_type"),
    body_fallback_child_types=("class_body", "protocol_body", "function_body", "enum_class_body"),
    function_boundary_types=frozenset({
        "function_declaration", "init_declaration",
        "deinit_declaration", "subscript_declaration",
    }),
    import_handler=_import_swift,
)

# Placeholder configs — these languages use custom extractors in extract-custom-languages.py
_ZIG_CONFIG = None
_POWERSHELL_CONFIG = None
_ELIXIR_CONFIG = None

# ── Extension → config dispatch map ──────────────────────────────────────────

EXTENSION_TO_CONFIG: dict[str, LanguageConfig | None] = {
    ".py":    _PYTHON_CONFIG,
    ".js":    _JS_CONFIG,
    ".ts":    _TS_CONFIG,
    ".tsx":   _TS_CONFIG,
    ".java":  _JAVA_CONFIG,
    ".c":     _C_CONFIG,
    ".h":     _C_CONFIG,
    ".cpp":   _CPP_CONFIG,
    ".cc":    _CPP_CONFIG,
    ".cxx":   _CPP_CONFIG,
    ".hpp":   _CPP_CONFIG,
    ".rb":    _RUBY_CONFIG,
    ".cs":    _CSHARP_CONFIG,
    ".kt":    _KOTLIN_CONFIG,
    ".kts":   _KOTLIN_CONFIG,
    ".scala": _SCALA_CONFIG,
    ".php":   _PHP_CONFIG,
    ".lua":   _LUA_CONFIG,
    ".toc":   _LUA_CONFIG,
    ".swift": _SWIFT_CONFIG,
    # custom extractors — None signals "use dedicated function"
    ".go":    None,
    ".rs":    None,
    ".zig":   None,
    ".ps1":   None,
    ".ex":    None,
    ".exs":   None,
}
