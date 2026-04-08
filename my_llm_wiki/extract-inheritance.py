# inheritance extraction — per-language parsers for extends/implements relations
# Adds typed `extends` (class parent) and `implements` (interface) edges
from __future__ import annotations

import importlib

_core = importlib.import_module("my_llm_wiki.extract-core")
_read_text = _core._read_text
_make_id = _core._make_id


def _add_base(
    base_name: str,
    relation: str,
    class_nid: str,
    line: int,
    stem: str,
    nodes: list,
    edges: list,
    seen_ids: set,
    str_path: str,
) -> None:
    """Add an extends/implements edge from class to base type.

    Creates a placeholder node for the base if not already in the graph.
    """
    base_name = base_name.strip()
    if not base_name:
        return
    # Strip generic parameters: List<String> -> List
    base_name = base_name.split("<")[0].split("[")[0].strip()
    if not base_name or not base_name[0].isalpha() and base_name[0] != "_":
        return

    base_nid = _make_id(stem, base_name)
    if base_nid not in seen_ids:
        # Try global (cross-file) ID
        base_nid = _make_id(base_name)
        if base_nid not in seen_ids:
            nodes.append({
                "id": base_nid, "label": base_name, "file_type": "code",
                "source_file": "", "source_location": "",
            })
            seen_ids.add(base_nid)
    edges.append({
        "source": class_nid, "target": base_nid, "relation": relation,
        "confidence": "EXTRACTED", "source_file": str_path,
        "source_location": f"L{line}", "weight": 1.0,
    })


def extract_python_inheritance(node, source, class_nid, class_name, line, stem,
                                nodes, edges, seen_ids, str_path) -> None:
    """Python: class Foo(Base1, Base2, metaclass=...): → extends only."""
    args = node.child_by_field_name("superclasses")
    if not args:
        return
    for arg in args.children:
        if arg.type == "identifier":
            base = _read_text(arg, source)
            _add_base(base, "extends", class_nid, line, stem, nodes, edges, seen_ids, str_path)
        elif arg.type == "attribute":
            # module.Class → take the full qualified name
            base = _read_text(arg, source)
            _add_base(base.rsplit(".", 1)[-1], "extends", class_nid, line, stem, nodes, edges, seen_ids, str_path)


def extract_java_inheritance(node, source, class_nid, class_name, line, stem,
                              nodes, edges, seen_ids, str_path) -> None:
    """Java: class Foo extends Bar implements I1, I2 { ... }
    Interfaces: interface Foo extends I1, I2 { ... }
    """
    is_interface = node.type == "interface_declaration"
    for child in node.children:
        if child.type == "superclass":
            # `extends Bar` (class only). Children: 'extends' keyword, type_identifier or generic_type
            for sub in child.children:
                if sub.type in ("type_identifier", "generic_type"):
                    base = _read_text(sub, source)
                    _add_base(base, "extends", class_nid, line, stem, nodes, edges, seen_ids, str_path)
        elif child.type == "super_interfaces":
            # `implements I1, I2` (class). Structure: 'implements' keyword + type_list containing types
            relation = "extends" if is_interface else "implements"
            for sub in child.children:
                if sub.type == "type_list":
                    for t in sub.children:
                        if t.type in ("type_identifier", "generic_type"):
                            base = _read_text(t, source)
                            _add_base(base, relation, class_nid, line, stem, nodes, edges, seen_ids, str_path)
        elif child.type == "extends_interfaces":
            # interface extends I1, I2
            for sub in child.children:
                if sub.type == "type_list":
                    for t in sub.children:
                        if t.type in ("type_identifier", "generic_type"):
                            base = _read_text(t, source)
                            _add_base(base, "extends", class_nid, line, stem, nodes, edges, seen_ids, str_path)


def extract_kotlin_inheritance(node, source, class_nid, class_name, line, stem,
                                nodes, edges, seen_ids, str_path) -> None:
    """Kotlin: class Foo : Bar(), I1, I2 { ... }
    Cannot distinguish class vs interface without resolving — use `extends` for all.
    Structure: class_declaration → delegation_specifiers → delegation_specifier → user_type/constructor_invocation
    """
    for child in node.children:
        if child.type == "delegation_specifiers":
            for spec in child.children:
                if spec.type == "delegation_specifier":
                    for sub in spec.children:
                        if sub.type in ("user_type", "constructor_invocation"):
                            name = _read_text(sub, source).split("(")[0].split("<")[0]
                            _add_base(name, "extends", class_nid, line, stem,
                                      nodes, edges, seen_ids, str_path)


def extract_typescript_inheritance(node, source, class_nid, class_name, line, stem,
                                    nodes, edges, seen_ids, str_path) -> None:
    """TypeScript: class Foo extends Base implements I1, I2 { ... }
    Also: interface Foo extends I1, I2 { ... }
    """
    for child in node.children:
        if child.type == "class_heritage":
            for sub in child.children:
                if sub.type == "extends_clause":
                    for t in sub.children:
                        if t.type == "identifier":
                            base = _read_text(t, source)
                            _add_base(base, "extends", class_nid, line, stem, nodes, edges, seen_ids, str_path)
                elif sub.type == "implements_clause":
                    for t in sub.children:
                        if t.type in ("type_identifier", "generic_type"):
                            base = _read_text(t, source)
                            _add_base(base, "implements", class_nid, line, stem, nodes, edges, seen_ids, str_path)
        elif child.type == "extends_type_clause":
            # interface extends I1, I2
            for t in child.children:
                if t.type in ("type_identifier", "generic_type"):
                    base = _read_text(t, source)
                    _add_base(base, "extends", class_nid, line, stem, nodes, edges, seen_ids, str_path)


def extract_csharp_inheritance(node, source, class_nid, class_name, line, stem,
                                nodes, edges, seen_ids, str_path) -> None:
    """C#: class Foo : Bar, IFoo, IBar { ... }
    First entry is base class if uppercase-starts, else interface. Convention: `I` prefix = interface.
    """
    for child in node.children:
        if child.type == "base_list":
            first = True
            for sub in child.children:
                if sub.type in ("identifier", "identifier_name", "qualified_name",
                                 "generic_name", "base_type"):
                    base = _read_text(sub, source).split("<")[0]
                    # Convention: `I` prefix = interface, else first is class base
                    if len(base) > 1 and base[0] == "I" and base[1].isupper():
                        relation = "implements"
                    elif first:
                        relation = "extends"
                    else:
                        relation = "implements"
                    _add_base(base, relation, class_nid, line, stem, nodes, edges, seen_ids, str_path)
                    first = False


def extract_cpp_inheritance(node, source, class_nid, class_name, line, stem,
                             nodes, edges, seen_ids, str_path) -> None:
    """C++: class Foo : public Base1, private Base2 { ... }"""
    for child in node.children:
        if child.type == "base_class_clause":
            for sub in child.children:
                if sub.type == "type_identifier":
                    base = _read_text(sub, source)
                    _add_base(base, "extends", class_nid, line, stem, nodes, edges, seen_ids, str_path)


def extract_swift_inheritance(node, source, class_nid, class_name, line, stem,
                               nodes, edges, seen_ids, str_path) -> None:
    """Swift: class Foo : Base, Protocol1, Protocol2 { ... }
    Cannot distinguish class inheritance vs protocol conformance easily — use `extends`.
    """
    for child in node.children:
        if child.type == "inheritance_specifier":
            for sub in child.children:
                if sub.type in ("user_type", "type_identifier"):
                    base = _read_text(sub, source)
                    _add_base(base, "extends", class_nid, line, stem, nodes, edges, seen_ids, str_path)


def extract_php_inheritance(node, source, class_nid, class_name, line, stem,
                             nodes, edges, seen_ids, str_path) -> None:
    """PHP: class Foo extends Bar implements I1, I2 { ... }"""
    for child in node.children:
        if child.type == "base_clause":
            # `extends Bar`
            for sub in child.children:
                if sub.type == "name":
                    base = _read_text(sub, source)
                    _add_base(base, "extends", class_nid, line, stem, nodes, edges, seen_ids, str_path)
        elif child.type == "class_interface_clause":
            # `implements I1, I2`
            for sub in child.children:
                if sub.type == "name":
                    base = _read_text(sub, source)
                    _add_base(base, "implements", class_nid, line, stem, nodes, edges, seen_ids, str_path)


def extract_ruby_inheritance(node, source, class_nid, class_name, line, stem,
                              nodes, edges, seen_ids, str_path) -> None:
    """Ruby: class Foo < Bar ... end. Mixins via `include Mixin` inside body."""
    superclass = node.child_by_field_name("superclass")
    if superclass:
        # superclass child is a `constant` or `scope_resolution`
        for sub in superclass.children:
            if sub.type == "constant":
                base = _read_text(sub, source)
                _add_base(base, "extends", class_nid, line, stem, nodes, edges, seen_ids, str_path)


def extract_scala_inheritance(node, source, class_nid, class_name, line, stem,
                               nodes, edges, seen_ids, str_path) -> None:
    """Scala: class Foo extends Base with Trait1 with Trait2 { ... }
    First type = extends, `with T` = implements (trait mixin).
    """
    for child in node.children:
        if child.type == "extends_clause":
            first = True
            for sub in child.children:
                if sub.type in ("type_identifier", "generic_type"):
                    base = _read_text(sub, source).split("[")[0]
                    relation = "extends" if first else "implements"
                    _add_base(base, relation, class_nid, line, stem, nodes, edges, seen_ids, str_path)
                    first = False


# Dispatch by tree-sitter module name
_DISPATCH = {
    "tree_sitter_python": extract_python_inheritance,
    "tree_sitter_java": extract_java_inheritance,
    "tree_sitter_kotlin": extract_kotlin_inheritance,
    "tree_sitter_javascript": extract_typescript_inheritance,
    "tree_sitter_typescript": extract_typescript_inheritance,
    "tree_sitter_c_sharp": extract_csharp_inheritance,
    "tree_sitter_cpp": extract_cpp_inheritance,
    "tree_sitter_swift": extract_swift_inheritance,
    "tree_sitter_php": extract_php_inheritance,
    "tree_sitter_ruby": extract_ruby_inheritance,
    "tree_sitter_scala": extract_scala_inheritance,
}


def extract_inheritance(ts_module, node, source, class_nid, class_name, line,
                         stem, nodes, edges, seen_ids, str_path) -> None:
    """Dispatch to the language-specific inheritance extractor."""
    handler = _DISPATCH.get(ts_module)
    if handler:
        handler(node, source, class_nid, class_name, line, stem,
                nodes, edges, seen_ids, str_path)
