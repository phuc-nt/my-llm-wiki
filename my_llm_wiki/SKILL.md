# my-llm-wiki

Turn any folder of code, docs, papers, or images into a queryable knowledge graph.

**Karpathy LLM Wiki concept**: drop raw files → compile once → query forever.

---

## What You Must Do When `/wiki` is Invoked

If no path given, use `.` (current directory). Follow these steps in order.

### Step 1 — Run structural extraction (AST + docs)

```bash
llm-wiki .
```

This runs: detect → AST extract (code) → structural extract (docs) → build → cluster → export.
Output goes to `wiki-out/`. Read the summary output.

### Step 2 — Semantic extraction (agent mode)

If detection found docs, papers, or images, enhance the graph with semantic extraction.

**Step 2a — Identify files needing semantic extraction:**

```bash
llm-wiki query stats
```

Check if there are document/paper nodes. If the graph is code-only, skip to Step 3.

**Step 2b — Read non-code files and extract entities:**

Split non-code files into chunks of 15-20 files. Dispatch subagents IN PARALLEL using the Agent tool — one per chunk. Each subagent receives this prompt:

```
You are a knowledge graph extraction agent. Read the files listed and extract entities and relationships.
Output ONLY valid JSON — no explanation, no markdown fences.

Files:
<FILE_LIST>

Rules:
- EXTRACTED: relationship explicit in source (citation, "see also", direct reference)
- INFERRED: reasonable inference (shared concept, implied dependency)
- AMBIGUOUS: uncertain — flag for review

For docs: extract named concepts, key terms, decisions, rationale.
For papers: extract claims, methods, citations, findings.
For images: use vision — describe components, relationships, purpose.

Output JSON:
{"nodes":[{"id":"filestem_entity","label":"Human Readable","file_type":"document|paper|image","source_file":"path","source_location":"L1"}],"edges":[{"source":"id","target":"id","relation":"references|cites|defines|explains|related_to|rationale_for","confidence":"EXTRACTED|INFERRED|AMBIGUOUS","source_file":"path"}]}
```

**Step 2c — Merge semantic results into graph:**

Collect JSON from all subagents. Write merged results to `wiki-out/semantic.json`:

```bash
python3 -c "
import json
from pathlib import Path
from my_llm_wiki import build, cluster, score_all, label_communities
from my_llm_wiki import god_nodes, surprising_connections, suggest_questions
from my_llm_wiki import generate, to_json, to_html, to_wiki, to_vault

# Load existing graph data
existing = json.loads(Path('wiki-out/graph.json').read_text())

# Load semantic results (paste collected JSON here or read from file)
semantic = json.loads(Path('wiki-out/semantic.json').read_text())

# Merge: existing + semantic
all_results = [
    {'nodes': [n for n in existing.get('nodes', [])], 'edges': [e for e in existing.get('links', [])]},
    semantic,
]
G = build(all_results)
communities = cluster(G)
cohesion = score_all(G, communities)
community_labels = label_communities(G, communities)

# Re-export everything
to_json(G, communities, 'wiki-out/graph.json')
to_html(G, communities, 'wiki-out/graph.html', community_labels)
to_wiki(G, communities, 'wiki-out/wiki', community_labels, cohesion, god_nodes(G))
to_vault(G, communities, 'wiki-out/vault', community_labels, cohesion)

report = generate(G, communities, cohesion, community_labels,
    god_nodes(G), surprising_connections(G, communities), {},
    token_cost={'input': 0, 'output': 0}, root='.',
    suggested_questions=suggest_questions(G, communities, community_labels))
Path('wiki-out/WIKI_REPORT.md').write_text(report)
print(f'Enhanced graph: {G.number_of_nodes()} nodes · {G.number_of_edges()} edges · {len(communities)} communities')
"
```

### Step 3 — Report results

Print summary and offer to answer questions:
```
Wiki built: X nodes · Y edges · Z communities
  graph.html  — interactive visualization
  WIKI_REPORT.md — analysis report
  vault/      — markdown vault

Ask me anything about the codebase, or run: llm-wiki query search <term>
```

---

## Querying the Graph

After building, query without re-reading source files:

```bash
llm-wiki query search GraphStore      # keyword search
llm-wiki query node GraphStore        # node details
llm-wiki query neighbors GraphStore   # direct connections
llm-wiki query community 0           # list community members
llm-wiki query path GraphStore Settings  # shortest path
llm-wiki query gods                   # most connected nodes
llm-wiki query stats                  # summary statistics
```

For natural language questions: read `wiki-out/WIKI_REPORT.md` for overview, use `llm-wiki query` for specifics.

---

## Key Concepts

- **3 confidence levels**: `EXTRACTED` (in source) · `INFERRED` (reasoned) · `AMBIGUOUS` (needs review)
- **Two-pass extraction**: AST (code, free) + semantic (agent, deep)
- **SHA256 cache**: re-runs only process changed files
- **Topology-based clustering**: Leiden/Louvain, no embeddings

---

## Installation

```bash
pip install my-llm-wiki

# Optional
pip install my-llm-wiki[all]   # PDF + .docx/.xlsx + Leiden clustering
```
