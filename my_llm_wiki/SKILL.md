# my-llm-wiki

Turn any folder of code, docs, papers, or images into a queryable knowledge graph with markdown-compatible output.

**Inspired by Andrej Karpathy's LLM Wiki concept**: drop raw files → compile once → query forever. No vector databases, no RAG pipelines. Just markdown, wikilinks, and a graph.

---

## How It Works

```
/raw  (your files)
  └─ detect → extract → build → cluster → analyze → report → export
                                                              ├─ wiki-out/graph.html     (interactive vis.js)
                                                              ├─ wiki-out/graph.json     (queryable graph)
                                                              ├─ wiki-out/WIKI_REPORT.md (audit trail)
                                                              ├─ wiki-out/wiki/          (Wikipedia-style articles)
                                                              └─ wiki-out/vault/      (markdown vault with [[wikilinks]])
```

---

## Usage

### Full pipeline on a folder

```python
/wiki .
```

This runs the complete pipeline:
1. Detect all code, docs, papers, images in the current folder
2. Extract structure (AST for code, LLM for docs/papers/images)
3. Build a NetworkX knowledge graph
4. Cluster into communities (Leiden/Louvain)
5. Analyze: god nodes, surprising connections, suggested questions
6. Export: JSON + HTML + wiki articles + markdown vault

### Pipeline (use in Claude Code sessions)

```python
from pathlib import Path
from my_llm_wiki import detect, extract, build, cluster, score_all
from my_llm_wiki import god_nodes, surprising_connections, suggest_questions
from my_llm_wiki import generate, to_json, to_html, to_wiki, to_vault

root = Path(".")

# 1. Detect files
info = detect(root)
print(f"{info['total_files']} files · {info['total_words']:,} words")
if info.get("warning"):
    print(f"Warning: {info['warning']}")

# 2. Extract (code=AST, docs/papers/images=LLM)
code_files = [Path(f) for f in info["files"]["code"]]
result = extract(code_files)

# 3. Build graph
G = build([result])

# 4. Cluster
communities = cluster(G)
cohesion = score_all(G, communities)
community_labels = {cid: f"Community {cid}" for cid in communities}

# 5. Analyze
nodes = god_nodes(G)
surprises = surprising_connections(G, communities)
questions = suggest_questions(G, communities, community_labels)

# 6. Report
report = generate(
    G, communities, cohesion, community_labels,
    nodes, surprises, info,
    token_cost={"input": 0, "output": 0},
    root=str(root),
    suggested_questions=questions,
)
Path("wiki-out/WIKI_REPORT.md").write_text(report)

# 7. Export
to_json(G, communities, "wiki-out/graph.json")
to_html(G, communities, "wiki-out/graph.html", community_labels)
to_wiki(G, communities, "wiki-out/wiki", community_labels, cohesion, nodes)
to_vault(G, communities, "wiki-out/vault", community_labels, cohesion)

print("Done. Open wiki-out/graph.html or wiki-out/vault/ in markdown.")
```

---

## Querying the Graph

After running the pipeline, query the graph without re-reading source files:

### CLI queries

```bash
llm-wiki query search GraphStore      # keyword search
llm-wiki query node GraphStore        # node details
llm-wiki query neighbors GraphStore   # direct connections
llm-wiki query community 0           # list community members
llm-wiki query path GraphStore Settings  # shortest path
llm-wiki query gods                   # most connected nodes
llm-wiki query stats                  # summary statistics
```

### As Claude Code skill (natural language)

When a user asks about the codebase structure, read `wiki-out/graph.json` and `wiki-out/WIKI_REPORT.md` to answer.
For specific topics, read the relevant `wiki-out/wiki/*.md` article.
For node-level detail, run `llm-wiki query` commands via Bash.

**Workflow**: user question → read WIKI_REPORT.md for overview → use `llm-wiki query` for specifics → answer.

---

## Outputs

| File | Description |
|------|-------------|
| `wiki-out/graph.html` | Interactive vis.js graph — click nodes, search, filter by community |
| `wiki-out/graph.json` | Persistent graph — query weeks later without re-reading |
| `wiki-out/WIKI_REPORT.md` | God nodes, surprising connections, suggested questions, knowledge gaps |
| `wiki-out/wiki/` | Wikipedia-style articles — one per community + god nodes |
| `wiki-out/vault/` | markdown vault — `[[wikilinks]]`, YAML frontmatter, `.vault/graph.json` |

---

## Key Concepts (Karpathy LLM Wiki)

- **Raw layer**: your original files — code, docs, papers, screenshots (never modified)
- **Wiki layer**: compiled knowledge — LLM-generated articles with cross-references
- **3 confidence levels**: `EXTRACTED` (found in source) · `INFERRED` (reasoned) · `AMBIGUOUS` (needs review)
- **Topology-based clustering**: no embeddings — Leiden finds communities by edge density
- **SHA256 cache**: re-runs only process changed files

---

## Ignore Files

Create `.wikiignore` to exclude paths (same syntax as `.gitignore`):

```
vendor/
node_modules/
dist/
*.generated.py
```

---

## Installation

```bash
pip install my-llm-wiki

# Optional extras
pip install my-llm-wiki[all]   # PDF + .docx/.xlsx + Leiden clustering
```
