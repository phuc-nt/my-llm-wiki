<p align="center">
  <img src="assets/logo.svg" width="120" alt="my-llm-wiki logo" />
</p>

<h1 align="center">my-llm-wiki</h1>

<p align="center">
  Turn any folder of code, docs, or papers into a queryable knowledge graph.
</p>

<p align="center">
  <a href="#install">Install</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#how-it-works">How It Works</a> ·
  <a href="#outputs">Outputs</a> ·
  <a href="#why">Why</a>
</p>

---

## The Idea

In April 2026, Andrej Karpathy shared a concept he called **LLM Wiki** — a personal knowledge system where you drop raw files into a folder and an LLM compiles them into a structured, interlinked wiki. No vector databases. No RAG pipelines. Just markdown and a graph.

The core insight: **compile once, query forever.**

> *"A large fraction of my recent token throughput has gone not into manipulating code, but into manipulating knowledge."*
> — Andrej Karpathy

`my-llm-wiki` brings this idea to life. Drop your code, docs, or papers into a folder. Run the pipeline. Get an interactive knowledge graph, Wikipedia-style articles, and a markdown vault with `[[wikilinks]]` — all from a single command.

---

## Install

```bash
pip install -e .
```

Optional extras:

```bash
pip install -e .[pdf]      # PDF support
pip install -e .[leiden]   # Better community detection
pip install -e .[office]   # .docx + .xlsx support
pip install -e .[all]      # Everything
```

---

## Quick Start

### CLI

```bash
llm-wiki .                  # scan current folder
llm-wiki /path/to/project   # scan specific folder
python -m my_llm_wiki .     # alternative
```

Output goes to `wiki-out/`.

### Python API

```python
from pathlib import Path
from my_llm_wiki import detect, extract, build, cluster, score_all
from my_llm_wiki import god_nodes, surprising_connections, suggest_questions
from my_llm_wiki import generate, to_json, to_html, to_wiki, to_vault

root = Path(".")

# 1. Detect files
info = detect(root)

# 2. Extract structure (AST for code — no LLM needed)
code_files = [Path(f) for f in info["files"]["code"]]
result = extract(code_files)

# 3. Build knowledge graph
G = build([result])

# 4. Cluster into communities
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
```

---

## How It Works

```
your-files/
  └─ detect → extract → build → cluster → analyze → report → export
                                                              ├─ graph.html    (interactive vis.js)
                                                              ├─ graph.json    (queryable graph)
                                                              ├─ WIKI_REPORT.md
                                                              ├─ wiki/         (Wikipedia-style articles)
                                                              └─ vault/        (markdown vault with [[wikilinks]])
```

### Pipeline

| Stage | What it does |
|-------|-------------|
| **detect** | Scan folder for code, docs, papers, images. Respects `.wikiignore` |
| **extract** | Parse structure via tree-sitter AST (16+ languages). No LLM for code |
| **build** | Assemble a NetworkX knowledge graph from nodes and edges |
| **cluster** | Find communities via Leiden/Louvain — topology-based, no embeddings |
| **analyze** | Identify god nodes, surprising connections, suggested questions |
| **report** | Generate a markdown audit trail |
| **export** | Output JSON + interactive HTML + wiki articles + markdown vault |

### Supported Languages

Python · JavaScript · TypeScript · Go · Rust · Java · C · C++ · Ruby · C# · Kotlin · Scala · PHP · Swift · Lua · Zig · PowerShell · Elixir

---

## Outputs

| Output | Description |
|--------|-------------|
| `wiki-out/graph.html` | Interactive vis.js graph — click nodes, search, filter by community |
| `wiki-out/graph.json` | Persistent graph — query weeks later without re-reading files |
| `wiki-out/WIKI_REPORT.md` | God nodes, surprising connections, suggested questions, knowledge gaps |
| `wiki-out/wiki/` | Wikipedia-style articles — one per community + god nodes |
| `wiki-out/vault/` | Markdown vault — `[[wikilinks]]`, YAML frontmatter, `.vault/graph.json` |

---

## Why

Karpathy's LLM Wiki concept has three layers:

1. **Raw layer** — your original files (never modified)
2. **Wiki layer** — compiled knowledge with cross-references
3. **Schema layer** — rules for how the wiki is structured

`my-llm-wiki` implements this as a deterministic pipeline. Code files get parsed by tree-sitter AST — no LLM calls, no API keys, no hallucination. The result is a knowledge graph you can browse, query, and explore.

### Design Principles

- **Compile once, query forever** — no re-reading source files on every question
- **No vector databases** — at personal scale, graph topology beats embeddings
- **Three confidence levels** — `EXTRACTED` (found in source), `INFERRED` (reasoned), `AMBIGUOUS` (needs review)
- **SHA256 cache** — re-runs only process changed files
- **Vault-ready** — wikilinks, YAML frontmatter, graph coloring, community tags

---

## Ignore Files

Create `.wikiignore` in your project root (same syntax as `.gitignore`):

```
vendor/
node_modules/
dist/
*.generated.py
```

---

## License

[MIT](LICENSE)
