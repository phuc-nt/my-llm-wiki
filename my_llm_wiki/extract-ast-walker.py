# generic AST extractor driven by LanguageConfig — handles all tree-sitter-backed languages
from __future__ import annotations

import importlib
from pathlib import Path

_core = importlib.import_module("my_llm_wiki.extract-core")
_cg = importlib.import_module("my_llm_wiki.extract-call-graph")
_cfgs = importlib.import_module("my_llm_wiki.extract-language-configs")
_inherit = importlib.import_module("my_llm_wiki.extract-inheritance")
_sigs = importlib.import_module("my_llm_wiki.extract-signatures")

_make_id = _core._make_id
_read_text = _core._read_text
_find_body = _core._find_body
LanguageConfig = _core.LanguageConfig

build_label_index = _cg.build_label_index
walk_calls = _cg.walk_calls

extract_inheritance = _inherit.extract_inheritance
extract_signature = _sigs.extract_signature

_js_extra_walk = _cfgs._js_extra_walk
_csharp_extra_walk = _cfgs._csharp_extra_walk
_swift_extra_walk = _cfgs._swift_extra_walk


def _extract_generic(path: Path, config: LanguageConfig) -> dict:
    """Generic AST extractor driven by LanguageConfig."""
    try:
        mod = importlib.import_module(config.ts_module)
        from tree_sitter import Language, Parser
        lang_fn = getattr(mod, config.ts_language_fn, None)
        if lang_fn is None:
            lang_fn = getattr(mod, "language", None)
        if lang_fn is None:
            return {"nodes": [], "edges": [], "error": f"No language function in {config.ts_module}"}
        language = Language(lang_fn())
    except ImportError:
        return {"nodes": [], "edges": [], "error": f"{config.ts_module} not installed"}
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}

    try:
        parser = Parser(language)
        source = path.read_bytes()
        tree = parser.parse(source)
        root = tree.root_node
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e)}

    stem = path.stem
    str_path = str(path)
    nodes: list[dict] = []
    edges: list[dict] = []
    seen_ids: set[str] = set()
    function_bodies: list[tuple[str, object]] = []

    def add_node(nid: str, label: str, line: int, signature: str = "") -> None:
        if nid not in seen_ids:
            seen_ids.add(nid)
            node = {
                "id": nid, "label": label, "file_type": "code",
                "source_file": str_path, "source_location": f"L{line}",
            }
            if signature:
                node["signature"] = signature
            nodes.append(node)

    def add_edge(src: str, tgt: str, relation: str, line: int,
                 confidence: str = "EXTRACTED", weight: float = 1.0) -> None:
        edges.append({
            "source": src, "target": tgt, "relation": relation,
            "confidence": confidence, "source_file": str_path,
            "source_location": f"L{line}", "weight": weight,
        })

    file_nid = _make_id(stem)
    add_node(file_nid, path.name, 1)

    def walk(node, parent_class_nid: str | None = None) -> None:
        t = node.type

        if t in config.import_types:
            if config.import_handler:
                config.import_handler(node, source, file_nid, stem, edges, str_path)
            return

        if t in config.class_types:
            name_node = node.child_by_field_name(config.name_field)
            if name_node is None:
                for child in node.children:
                    if child.type in config.name_fallback_child_types:
                        name_node = child
                        break
            if not name_node:
                return
            class_name = _read_text(name_node, source)
            class_nid = _make_id(stem, class_name)
            line = node.start_point[0] + 1
            add_node(class_nid, class_name, line)
            add_edge(file_nid, class_nid, "contains", line)

            # Extract extends/implements edges (per-language dispatch)
            extract_inheritance(
                config.ts_module, node, source, class_nid, class_name, line,
                stem, nodes, edges, seen_ids, str_path,
            )

            body = _find_body(node, config)
            if body:
                for child in body.children:
                    walk(child, parent_class_nid=class_nid)
            return

        if t in config.function_types:
            if t == "deinit_declaration":
                func_name: str | None = "deinit"
            elif t == "subscript_declaration":
                func_name = "subscript"
            elif config.resolve_function_name_fn is not None:
                declarator = node.child_by_field_name("declarator")
                func_name = None
                if declarator:
                    func_name = config.resolve_function_name_fn(declarator, source)
            else:
                name_node = node.child_by_field_name(config.name_field)
                if name_node is None:
                    for child in node.children:
                        if child.type in config.name_fallback_child_types:
                            name_node = child
                            break
                func_name = _read_text(name_node, source) if name_node else None

            if not func_name:
                return

            line = node.start_point[0] + 1
            signature = extract_signature(config.ts_module, node, source)
            if parent_class_nid:
                func_nid = _make_id(parent_class_nid, func_name)
                add_node(func_nid, f".{func_name}()", line, signature)
                add_edge(parent_class_nid, func_nid, "method", line)
            else:
                func_nid = _make_id(stem, func_name)
                add_node(func_nid, f"{func_name}()", line, signature)
                add_edge(file_nid, func_nid, "contains", line)

            body = _find_body(node, config)
            if body:
                function_bodies.append((func_nid, body))
            return

        # Language-specific extra handlers
        if config.ts_module in ("tree_sitter_javascript", "tree_sitter_typescript"):
            if _js_extra_walk(node, source, file_nid, stem, str_path,
                              nodes, edges, seen_ids, function_bodies,
                              parent_class_nid, add_node, add_edge):
                return

        if config.ts_module == "tree_sitter_c_sharp":
            if _csharp_extra_walk(node, source, file_nid, stem, str_path,
                                   nodes, edges, seen_ids, function_bodies,
                                   parent_class_nid, add_node, add_edge, walk):
                return

        if config.ts_module == "tree_sitter_swift":
            if _swift_extra_walk(node, source, file_nid, stem, str_path,
                                  nodes, edges, seen_ids, function_bodies,
                                  parent_class_nid, add_node, add_edge):
                return

        for child in node.children:
            walk(child, parent_class_nid=None)

    walk(root)

    # Call-graph pass
    label_to_nid = build_label_index(nodes)
    seen_call_pairs: set[tuple[str, str]] = set()
    for caller_nid, body_node in function_bodies:
        walk_calls(body_node, caller_nid, config, source,
                   label_to_nid, seen_call_pairs, edges, str_path)

    # Clean edges: drop edges whose source is not in valid_ids,
    # but keep import edges pointing to external modules
    valid_ids = seen_ids
    clean_edges = [
        e for e in edges
        if e["source"] in valid_ids
        and (e["target"] in valid_ids or e["relation"] in ("imports", "imports_from"))
    ]

    return {"nodes": nodes, "edges": clean_edges}
