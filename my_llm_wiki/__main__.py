# CLI entry point: python -m my_llm_wiki [path]
from __future__ import annotations

import sys
from pathlib import Path


_VERSION = "0.2.2"

_HELP = f"""\
my-llm-wiki v{_VERSION} — turn any folder into a queryable knowledge graph

Usage:
  llm-wiki [path]                    Build graph (default: current dir)
  llm-wiki query <command> [args]    Query the built graph
  llm-wiki watch [path] [interval]   Auto-rebuild on file changes
  llm-wiki add <url> [--author name] Fetch URL, save as markdown

Query commands:
  search <terms>   node <label>      neighbors <label>
  community <id>   path <A> <B>      gods     stats

Options:
  --version        Show version
  --help, -h       Show this help
  --no-viz         Skip HTML visualization (for large graphs)
"""


def main() -> None:
    # Handle --version and --help before path parsing
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        print(f"my-llm-wiki {_VERSION}")
        return
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print(_HELP)
        return

    # Route subcommands
    if len(sys.argv) > 1 and sys.argv[1] == "query":
        import importlib
        _query = importlib.import_module("my_llm_wiki.query-graph")
        _query.query_main(sys.argv[2:])
        return

    if len(sys.argv) > 1 and sys.argv[1] == "watch":
        import importlib
        _watch = importlib.import_module("my_llm_wiki.watch-folder")
        watch_target = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
        interval = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        _watch.watch(watch_target, interval)
        return

    if len(sys.argv) > 1 and sys.argv[1] == "add":
        import importlib
        _ingest = importlib.import_module("my_llm_wiki.ingest-url")
        if len(sys.argv) < 3:
            print("Usage: llm-wiki add <url> [--author <name>]")
            sys.exit(1)
        url = sys.argv[2]
        author = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--author" else None
        _ingest.ingest(url, author=author)
        print("[wiki] Run `llm-wiki .` to rebuild the graph with ingested content.")
        return

    # Parse flags
    no_viz = "--no-viz" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    target = Path(args[0]) if args else Path(".")
    if not target.exists():
        print(f"[wiki] Path not found: {target}")
        sys.exit(1)

    from my_llm_wiki import (
        detect, extract, extract_docs, build, cluster, score_all,
        label_communities, cross_reference,
        god_nodes, surprising_connections, suggest_questions,
        generate, to_json, to_html, to_wiki, to_vault,
    )

    out = Path("wiki-out")
    out.mkdir(exist_ok=True)

    # 1. Detect
    print(f"[wiki] Scanning {target.resolve()} ...")
    info = detect(target)
    total = info["total_files"]
    words = info["total_words"]
    print(f"[wiki] Found {total} files · {words:,} words")
    if info.get("warning"):
        print(f"[wiki] Warning: {info['warning']}")

    # 2. Extract
    results: list[dict] = []

    code_files = [Path(f) for f in info["files"].get("code", [])]
    if code_files:
        print(f"[wiki] Extracting AST from {len(code_files)} code files ...")
        code_result = extract(code_files)
        results.append(code_result)
        print(f"[wiki] Code: {len(code_result.get('nodes', []))} nodes · {len(code_result.get('edges', []))} edges")

    doc_files = [Path(f) for f in info["files"].get("document", [])]
    paper_files = [Path(f) for f in info["files"].get("paper", [])]
    all_doc_files = doc_files + paper_files
    if all_doc_files:
        print(f"[wiki] Extracting from {len(all_doc_files)} docs/papers ...")
        doc_result = extract_docs(all_doc_files, target)
        results.append(doc_result)
        print(f"[wiki] Docs: {len(doc_result.get('nodes', []))} nodes · {len(doc_result.get('edges', []))} edges")

    # Create hub nodes for image files (content extraction needs agent mode)
    image_files = info["files"].get("image", [])
    if image_files:
        img_nodes = [
            {"id": f"img_{i}", "label": Path(f).stem, "file_type": "image",
             "source_file": str(Path(f).relative_to(target) if Path(f).is_absolute() else f),
             "source_location": ""}
            for i, f in enumerate(image_files)
        ]
        results.append({"nodes": img_nodes, "edges": []})
        print(f"[wiki] Images: {len(image_files)} files (use agent mode for content extraction)")

    if not results:
        print("[wiki] No supported files found. Nothing to extract.")
        sys.exit(0)

    # 3. Build
    G = build(results)

    # 3b. Cross-reference code ↔ docs
    if code_files and all_doc_files:
        xref_edges = cross_reference(G, target)
        if xref_edges:
            for e in xref_edges:
                G.add_edge(e["source"], e["target"], **{k: v for k, v in e.items() if k not in ("source", "target")})
            print(f"[wiki] Cross-ref: {len(xref_edges)} code↔doc edges")

    print(f"[wiki] Graph: {G.number_of_nodes()} nodes · {G.number_of_edges()} edges")

    # 4. Cluster
    communities = cluster(G)
    cohesion = score_all(G, communities)
    community_labels = label_communities(G, communities)
    print(f"[wiki] {len(communities)} communities detected")

    # 5. Analyze
    nodes = god_nodes(G)
    surprises = surprising_connections(G, communities)
    questions = suggest_questions(G, communities, community_labels)

    # 6. Report
    report = generate(
        G, communities, cohesion, community_labels,
        nodes, surprises, info,
        token_cost={"input": 0, "output": 0},
        root=str(target),
        suggested_questions=questions,
    )
    (out / "WIKI_REPORT.md").write_text(report, encoding="utf-8")

    # 7. Export
    to_json(G, communities, str(out / "graph.json"))
    if not no_viz:
        to_html(G, communities, str(out / "graph.html"), community_labels)
    else:
        print("[wiki] Skipping HTML visualization (--no-viz)")
    to_wiki(G, communities, str(out / "wiki"), community_labels, cohesion, nodes)
    to_vault(G, communities, str(out / "vault"), community_labels, cohesion)

    print(f"[wiki] Done. Output in {out.resolve()}/")
    print(f"  graph.html  — interactive visualization")
    print(f"  graph.json  — queryable graph data")
    print(f"  WIKI_REPORT.md — analysis report")
    print(f"  wiki/       — Wikipedia-style articles")
    print(f"  vault/      — markdown vault with [[wikilinks]]")


if __name__ == "__main__":
    main()
