# public API for AST extraction — dispatcher, collect_files, main extract()
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

_walker = importlib.import_module("my_llm_wiki.extract-ast-walker")
_cfgs = importlib.import_module("my_llm_wiki.extract-language-configs")
_custom = importlib.import_module("my_llm_wiki.extract-custom-languages")
_custom2 = importlib.import_module("my_llm_wiki.extract-custom-languages-2")
_elixir_mod = importlib.import_module("my_llm_wiki.extract-elixir")
_postprocess = importlib.import_module("my_llm_wiki.extract-python-postprocess")
_cache = importlib.import_module("my_llm_wiki.cache-file-hash")

_extract_generic = _walker._extract_generic
load_cached = _cache.load_cached
save_cached = _cache.save_cached

extract_python_rationale = _postprocess.extract_python_rationale
resolve_cross_file_imports = _postprocess.resolve_cross_file_imports

extract_go = _custom.extract_go
extract_rust = _custom.extract_rust
extract_zig = _custom2.extract_zig
extract_powershell = _custom2.extract_powershell
extract_elixir = _elixir_mod.extract_elixir


# ── Per-language extract functions (generic-backed) ───────────────────────────

def extract_python(path: Path) -> dict:
    result = _extract_generic(path, _cfgs._PYTHON_CONFIG)
    if "error" not in result:
        extract_python_rationale(path, result)
    return result


def extract_js(path: Path) -> dict:
    config = _cfgs._TS_CONFIG if path.suffix in (".ts", ".tsx") else _cfgs._JS_CONFIG
    return _extract_generic(path, config)


def extract_java(path: Path) -> dict:
    return _extract_generic(path, _cfgs._JAVA_CONFIG)


def extract_c(path: Path) -> dict:
    return _extract_generic(path, _cfgs._C_CONFIG)


def extract_cpp(path: Path) -> dict:
    return _extract_generic(path, _cfgs._CPP_CONFIG)


def extract_ruby(path: Path) -> dict:
    return _extract_generic(path, _cfgs._RUBY_CONFIG)


def extract_csharp(path: Path) -> dict:
    return _extract_generic(path, _cfgs._CSHARP_CONFIG)


def extract_kotlin(path: Path) -> dict:
    return _extract_generic(path, _cfgs._KOTLIN_CONFIG)


def extract_scala(path: Path) -> dict:
    return _extract_generic(path, _cfgs._SCALA_CONFIG)


def extract_php(path: Path) -> dict:
    return _extract_generic(path, _cfgs._PHP_CONFIG)


def extract_lua(path: Path) -> dict:
    return _extract_generic(path, _cfgs._LUA_CONFIG)


def extract_swift(path: Path) -> dict:
    return _extract_generic(path, _cfgs._SWIFT_CONFIG)


# ── Dispatch table ────────────────────────────────────────────────────────────

_DISPATCH: dict[str, Any] = {
    ".py":    extract_python,
    ".js":    extract_js,    ".ts":   extract_js,   ".tsx":  extract_js,
    ".go":    extract_go,    ".rs":   extract_rust,
    ".java":  extract_java,
    ".c":     extract_c,     ".h":    extract_c,
    ".cpp":   extract_cpp,   ".cc":   extract_cpp,  ".cxx":  extract_cpp, ".hpp": extract_cpp,
    ".rb":    extract_ruby,  ".cs":   extract_csharp,
    ".kt":    extract_kotlin, ".kts": extract_kotlin,
    ".scala": extract_scala, ".php":  extract_php,
    ".swift": extract_swift, ".lua":  extract_lua,  ".toc":  extract_lua,
    ".zig":   extract_zig,   ".ps1":  extract_powershell,
    ".ex":    extract_elixir, ".exs": extract_elixir,
}


# ── Main entry points ─────────────────────────────────────────────────────────

def extract(paths: list[Path]) -> dict:
    """Extract AST nodes and edges from a list of code files.

    Two-pass: per-file structural extraction, then cross-file Python import resolution.
    Results are cached by file hash — unchanged files are skipped on re-runs.
    """
    per_file: list[dict] = []

    # Infer a common root for cache key namespacing
    try:
        if not paths:
            root = Path(".")
        elif len(paths) == 1:
            root = paths[0].parent
        else:
            common_len = sum(
                1 for i in range(min(len(p.parts) for p in paths))
                if len({p.parts[i] for p in paths}) == 1
            )
            root = Path(*paths[0].parts[:common_len]) if common_len else Path(".")
    except Exception:
        root = Path(".")

    total = len(paths)
    for i, path in enumerate(paths, 1):
        extractor = _DISPATCH.get(path.suffix)
        if extractor is None:
            continue
        cached = load_cached(path, root)
        if cached is not None:
            per_file.append(cached)
            continue
        # Progress indicator for large codebases
        if total > 50 and i % 50 == 0:
            import sys
            print(f"\r[wiki] AST: {i}/{total} files ({i*100//total}%)", end="", flush=True, file=sys.stderr)
        result = extractor(path)
        if "error" not in result:
            save_cached(path, result, root)
        per_file.append(result)
    if total > 50:
        import sys
        print(f"\r[wiki] AST: {total}/{total} (100%)          ", file=sys.stderr)

    all_nodes: list[dict] = []
    all_edges: list[dict] = []
    for result in per_file:
        all_nodes.extend(result.get("nodes", []))
        all_edges.extend(result.get("edges", []))

    # Cross-file class-level edges (Python only)
    py_paths = [p for p in paths if p.suffix == ".py"]
    py_results = [r for r, p in zip(per_file, paths) if p.suffix == ".py"]
    all_edges.extend(resolve_cross_file_imports(py_results, py_paths))

    # Enrich nodes with doc comments (Javadoc, JSDoc, GoDoc, etc.)
    try:
        _doc_comments = importlib.import_module("my_llm_wiki.extract-doc-comments")
        _doc_comments.enrich_nodes_with_comments(all_nodes, all_edges, paths)
    except Exception:
        pass

    return {"nodes": all_nodes, "edges": all_edges, "input_tokens": 0, "output_tokens": 0}


def collect_files(target: Path) -> list[Path]:
    """Collect all supported source files under target (file or directory)."""
    if target.is_file():
        return [target]
    _EXTENSIONS = (
        "*.py", "*.js", "*.ts", "*.tsx", "*.go", "*.rs",
        "*.java", "*.c", "*.h", "*.cpp", "*.cc", "*.cxx", "*.hpp",
        "*.rb", "*.cs", "*.kt", "*.kts", "*.scala", "*.php", "*.swift",
        "*.lua", "*.toc", "*.zig", "*.ps1", "*.ex", "*.exs",
    )
    results: list[Path] = []
    for pattern in _EXTENSIONS:
        results.extend(
            p for p in target.rglob(pattern)
            if not any(part.startswith(".") for part in p.parts)
        )
    return sorted(results)
