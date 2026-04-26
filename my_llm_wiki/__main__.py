# CLI entry point: python -m my_llm_wiki [path]
from __future__ import annotations

import sys
from pathlib import Path


_VERSION = "0.6.0"

_HELP = f"""\
my-llm-wiki v{_VERSION} — turn any folder into a queryable knowledge graph

Usage:
  llm-wiki [path]                    Build graph (default: current dir)
  llm-wiki query <command> [args]    Query the built graph
  llm-wiki lint                      Graph health check
  llm-wiki watch [path] [interval]   Auto-rebuild on file changes
  llm-wiki add <url> [--author name] Fetch URL, save as markdown
  llm-wiki note <text> [opts]        File an insight into wiki-out/ingested/

Query commands:
  search <terms>   node <label>      neighbors <label>
  community <id>   path <A> <B>      gods     stats

Note options:
  --link <label>   Link to an existing node (repeatable)
  --tag <name>     Tag the insight (repeatable)
  --title <text>   Custom heading (default: first line of text)
  --allow-secrets  Skip secret/API-key scan (use only for false positives)

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

    if len(sys.argv) > 1 and sys.argv[1] == "lint":
        import importlib
        import json
        from networkx.readwrite import json_graph
        graph_path = Path("wiki-out/graph.json")
        if not graph_path.exists():
            print("[wiki] No graph found. Run `llm-wiki .` first.")
            sys.exit(1)
        import networkx as nx
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        G = json_graph.node_link_graph(data, edges="links")
        n, e = G.number_of_nodes(), G.number_of_edges()
        # Orphans: nodes with 0 edges
        orphans = [nid for nid in G.nodes() if G.degree(nid) == 0]
        # Confidence breakdown
        confs = [d.get("confidence", "EXTRACTED") for _, _, d in G.edges(data=True)]
        total_e = len(confs) or 1
        ext_pct = round(confs.count("EXTRACTED") / total_e * 100)
        inf_pct = round(confs.count("INFERRED") / total_e * 100)
        amb_pct = round(confs.count("AMBIGUOUS") / total_e * 100)
        # Communities
        _analyze = importlib.import_module("my_llm_wiki.analyze-graph")
        communities = {}
        for nid, d in G.nodes(data=True):
            cid = d.get("community")
            if cid is not None:
                communities.setdefault(int(cid), []).append(nid)
        tiny = [cid for cid, members in communities.items() if len(members) <= 2]
        # Report
        print(f"Wiki Health Check")
        print(f"  Nodes: {n} · Edges: {e} · Communities: {len(communities)}")
        print(f"  Confidence: {ext_pct}% EXTRACTED · {inf_pct}% INFERRED · {amb_pct}% AMBIGUOUS")
        if orphans:
            print(f"  Orphan nodes (no edges): {len(orphans)}")
            for o in orphans[:5]:
                print(f"    - {G.nodes[o].get('label', o)}")
            if len(orphans) > 5:
                print(f"    ... and {len(orphans) - 5} more")
        else:
            print(f"  No orphan nodes")
        if tiny:
            print(f"  Tiny communities (<=2 nodes): {len(tiny)}")
        if amb_pct > 10:
            print(f"  High ambiguity ({amb_pct}%) — review AMBIGUOUS edges")
        return

    if len(sys.argv) > 1 and sys.argv[1] == "note":
        from my_llm_wiki import write_note
        note_args = sys.argv[2:]
        if not note_args:
            print("Usage: llm-wiki note <text> [--link <label>] [--tag <name>] [--title <text>]")
            sys.exit(1)
        # Parse flags; remaining positional tokens form the note text
        links: list[str] = []
        tags: list[str] = []
        title: str | None = None
        allow_secrets = False
        text_parts: list[str] = []
        i = 0
        while i < len(note_args):
            tok = note_args[i]
            if tok == "--link" and i + 1 < len(note_args):
                links.append(note_args[i + 1])
                i += 2
            elif tok == "--tag" and i + 1 < len(note_args):
                tags.append(note_args[i + 1])
                i += 2
            elif tok == "--title" and i + 1 < len(note_args):
                title = note_args[i + 1]
                i += 2
            elif tok == "--allow-secrets":
                allow_secrets = True
                i += 1
            else:
                text_parts.append(tok)
                i += 1
        text = " ".join(text_parts).strip()
        # Fall back to stdin if no positional text (for piped input)
        if not text and not sys.stdin.isatty():
            text = sys.stdin.read().strip()
        if not text:
            print("[wiki] Note text is empty. Provide text as arg or pipe via stdin.")
            sys.exit(1)
        try:
            path = write_note(
                text, title=title, links=links or None, tags=tags or None,
                allow_secrets=allow_secrets,
            )
        except ValueError as e:
            print(f"[wiki] {e}")
            sys.exit(1)
        print(f"[wiki] Note saved: {path}")
        print("[wiki] Run `llm-wiki .` to fold it into the graph.")
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
