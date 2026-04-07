# CLI entry point: python -m my_llm_wiki [path]
from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    if not target.exists():
        print(f"[wiki] Path not found: {target}")
        sys.exit(1)

    from my_llm_wiki import (
        detect, extract, build, cluster, score_all,
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
    code_files = [Path(f) for f in info["files"].get("code", [])]
    if not code_files:
        print("[wiki] No code files found. Nothing to extract.")
        sys.exit(0)
    print(f"[wiki] Extracting AST from {len(code_files)} code files ...")
    result = extract(code_files)
    nodes_count = len(result.get("nodes", []))
    edges_count = len(result.get("edges", []))
    print(f"[wiki] Extracted {nodes_count} nodes · {edges_count} edges")

    # 3. Build
    G = build([result])
    print(f"[wiki] Graph: {G.number_of_nodes()} nodes · {G.number_of_edges()} edges")

    # 4. Cluster
    communities = cluster(G)
    cohesion = score_all(G, communities)
    community_labels = {cid: f"Community {cid}" for cid in communities}
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
    to_html(G, communities, str(out / "graph.html"), community_labels)
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
