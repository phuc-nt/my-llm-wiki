# function signature extraction — adds `signature` field to function nodes
# Format: "(param: type, param: type) -> return_type"
from __future__ import annotations

import importlib
import os
import re

_core = importlib.import_module("my_llm_wiki.extract-core")
_read_text = _core._read_text

_DEBUG = os.environ.get("WIKI_DEBUG", "").lower() in ("1", "true", "yes")


_MAX_SIG_LEN = 200  # truncate very long signatures


def _clean(text: str) -> str:
    """Normalize whitespace in signature text."""
    return re.sub(r"\s+", " ", text).strip()


def _truncate(sig: str) -> str:
    """Truncate long signatures with ellipsis. Preserves display — does not try
    to produce balanced parens; rendering code should treat this as display text only.
    """
    if len(sig) <= _MAX_SIG_LEN:
        return sig
    return sig[:_MAX_SIG_LEN - 3] + "..."


def extract_python_signature(func_node, source) -> str:
    """Python: def foo(x: int, y: str = 'default') -> bool"""
    params = func_node.child_by_field_name("parameters")
    ret = func_node.child_by_field_name("return_type")
    params_text = _clean(_read_text(params, source)) if params else "()"
    ret_text = ""
    if ret:
        ret_text = f" -> {_clean(_read_text(ret, source))}"
    return _truncate(params_text + ret_text)


def extract_java_signature(func_node, source) -> str:
    """Java: public Foo method(int x, String y) throws Exception"""
    params = func_node.child_by_field_name("parameters")
    ret_type = func_node.child_by_field_name("type")
    params_text = _clean(_read_text(params, source)) if params else "()"
    ret_text = f": {_clean(_read_text(ret_type, source))}" if ret_type else ""
    return _truncate(params_text + ret_text)


def extract_typescript_signature(func_node, source) -> str:
    """TypeScript: (x: number, y: string): Promise<User>"""
    params = func_node.child_by_field_name("parameters")
    ret = func_node.child_by_field_name("return_type")
    params_text = _clean(_read_text(params, source)) if params else "()"
    ret_text = ""
    if ret:
        ret_text = _clean(_read_text(ret, source))
        if not ret_text.startswith(":"):
            ret_text = f": {ret_text}"
    return _truncate(params_text + ret_text)


def extract_kotlin_signature(func_node, source) -> str:
    """Kotlin: fun foo(x: Int, y: String): Boolean / fun bar(): T?"""
    # Kotlin tree-sitter: function_value_parameters + optional return type sibling
    params_node = None
    ret_type = None
    for child in func_node.children:
        if child.type == "function_value_parameters":
            params_node = child
        elif params_node is not None and child.type in (
            "user_type", "function_type", "nullable_type", "type_identifier",
            "generic_type", "parenthesized_type",
        ):
            ret_type = child
            break
    params_text = _clean(_read_text(params_node, source)) if params_node else "()"
    ret_text = f": {_clean(_read_text(ret_type, source))}" if ret_type else ""
    return _truncate(params_text + ret_text)


def extract_csharp_signature(func_node, source) -> str:
    """C#: public Task<User> GetUser(int id)"""
    params = func_node.child_by_field_name("parameters")
    ret_type = (func_node.child_by_field_name("returns")
                or func_node.child_by_field_name("type"))
    params_text = _clean(_read_text(params, source)) if params else "()"
    ret_text = f": {_clean(_read_text(ret_type, source))}" if ret_type else ""
    return _truncate(params_text + ret_text)


def extract_cpp_signature(func_node, source) -> str:
    """C/C++: int foo(const char* name, int count)
    The return type is a sibling, not a field. Extract from declarator.
    """
    declarator = func_node.child_by_field_name("declarator")
    if not declarator:
        return ""
    # Walk declarator to find parameter_list
    for child in declarator.children:
        if child.type == "parameter_list":
            params_text = _clean(_read_text(child, source))
            # Get return type from function_definition's type field
            ret_type = func_node.child_by_field_name("type")
            ret_text = f": {_clean(_read_text(ret_type, source))}" if ret_type else ""
            return _truncate(params_text + ret_text)
    return ""


def extract_scala_signature(func_node, source) -> str:
    """Scala: def foo(x: Int, y: String): Boolean"""
    params = None
    ret_type = None
    for child in func_node.children:
        if child.type == "parameters":
            params = child
        elif child.type == "type_identifier" and params is not None:
            ret_type = child
    params_text = _clean(_read_text(params, source)) if params else "()"
    ret_text = f": {_clean(_read_text(ret_type, source))}" if ret_type else ""
    return _truncate(params_text + ret_text)


def extract_php_signature(func_node, source) -> str:
    """PHP: function foo(int $x, string $y): array"""
    params = func_node.child_by_field_name("parameters")
    ret_type = func_node.child_by_field_name("return_type")
    params_text = _clean(_read_text(params, source)) if params else "()"
    ret_text = f": {_clean(_read_text(ret_type, source))}" if ret_type else ""
    return _truncate(params_text + ret_text)


def extract_swift_signature(func_node, source) -> str:
    """Swift: func foo(x: Int, y: String) -> Bool / func bar() -> String?"""
    # Swift: parameters are `parameter` nodes between ( and ),
    # return type is after `->`
    params = []
    seen_arrow = False
    ret_type = None
    for child in func_node.children:
        if child.type == "parameter":
            params.append(_clean(_read_text(child, source)))
        elif child.type == "->":
            seen_arrow = True
        elif seen_arrow and child.type in (
            "user_type", "optional_type", "type_identifier",
            "generic_type", "function_type", "tuple_type",
        ):
            ret_type = child
            break
    params_text = f"({', '.join(params)})"
    ret_text = f" -> {_clean(_read_text(ret_type, source))}" if ret_type else ""
    return _truncate(params_text + ret_text)


def extract_ruby_signature(func_node, source) -> str:
    """Ruby: def foo(x, y = default) — no type info, just param names."""
    params = func_node.child_by_field_name("parameters")
    if params:
        return _truncate(_clean(_read_text(params, source)))
    return "()"


def extract_js_signature(func_node, source) -> str:
    """JavaScript: function foo(x, y) — no type info, just param names."""
    params = func_node.child_by_field_name("parameters")
    if params:
        return _truncate(_clean(_read_text(params, source)))
    return "()"


_DISPATCH = {
    "tree_sitter_python": extract_python_signature,
    "tree_sitter_java": extract_java_signature,
    "tree_sitter_typescript": extract_typescript_signature,
    "tree_sitter_javascript": extract_js_signature,
    "tree_sitter_kotlin": extract_kotlin_signature,
    "tree_sitter_c_sharp": extract_csharp_signature,
    "tree_sitter_c": extract_cpp_signature,
    "tree_sitter_cpp": extract_cpp_signature,
    "tree_sitter_scala": extract_scala_signature,
    "tree_sitter_php": extract_php_signature,
    "tree_sitter_swift": extract_swift_signature,
    "tree_sitter_ruby": extract_ruby_signature,
}


def extract_signature(ts_module, func_node, source) -> str:
    """Extract function signature string. Returns empty string if unsupported or error."""
    handler = _DISPATCH.get(ts_module)
    if not handler:
        return ""
    try:
        return handler(func_node, source)
    except Exception as exc:
        if _DEBUG:
            import sys
            print(f"[wiki] signature extraction failed in {ts_module}: {exc}",
                  file=sys.stderr)
        return ""
