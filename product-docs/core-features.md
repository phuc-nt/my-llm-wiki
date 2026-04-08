---
layout: default
title: Core Features
nav_order: 3
description: "Two-pass extraction, cross-referencing, community detection, and 7 query commands."
---

# Core Features

## Two-pass extraction

### Pass 1 — Structural (free, deterministic)

Runs automatically with `llm-wiki .`:

- **Code** (18 languages) — tree-sitter AST extracts classes, functions, imports, call relationships
- **Markdown/text** — headings, bold definitions, cross-document links
- **DOCX/PDF** — converted to text, then parsed like markdown
- **Images** — hub nodes created (content needs agent mode)
- **Cross-reference** — code entities mentioned in docs get automatic `mentions` edges

### Pass 2 — Semantic (agent mode, deep)

Runs in Claude Code via `/wiki .` skill. Dispatches subagents to read files that structural extraction can't handle well:

| File Type | Structural result | Agent result |
|-----------|------------------|-------------|
| Code | Full AST | Not needed |
| Markdown | Headings + links | 2x entities |
| DOCX | Hub nodes only | **30x entities** |
| Scanned PDF | 0 text | **85x entities** |
| Images | Hub nodes only | **Vision extracts content** |

---

## Community detection

Leiden/Louvain algorithm groups related nodes into communities. No embeddings — pure topology.

- Adaptive resolution: dense graphs (code) get tighter communities, sparse graphs (docs) get broader grouping
- Semantic labels from top-degree nodes in each community
- Cohesion scores measure how tightly connected each community is
- Oversized communities auto-split

---

## Cross-reference code ↔ docs

When a codebase has both code and documentation, `my-llm-wiki` automatically creates `mentions` edges between doc nodes and code entities whose names appear in the text.

Example: if `README.md` mentions "GraphStore", the doc node gets an INFERRED edge to the `GraphStore` class node.

---

## Query commands

After building, query without re-reading source files:

```bash
llm-wiki query search <terms>       # keyword search across all nodes
llm-wiki query node <label>         # node details + source location
llm-wiki query neighbors <label>    # direct connections with edge types
llm-wiki query community <id>       # list community members by degree
llm-wiki query path <A> <B>         # shortest path between concepts
llm-wiki query gods                 # top 10 most connected nodes
llm-wiki query stats                # node/edge/community/confidence counts
```

---

## File watcher

```bash
llm-wiki watch .       # poll for changes, auto-rebuild
llm-wiki watch . 10    # custom interval (seconds)
```

---

## URL ingest

```bash
llm-wiki add https://example.com             # fetch page as markdown
llm-wiki add https://arxiv.org/pdf/... --author "Name"  # with metadata
```

Saved to `wiki-out/ingested/` with YAML frontmatter. Next `llm-wiki .` includes it.

---

## Schema rules

Create `.wikischema` in project root to define custom entity and relation types:

```json
{
  "entity_types": ["code", "document", "paper", "image", "concept"],
  "relation_types": ["imports", "calls", "references", "explains", "contradicts"]
}
```

Graph validation warns about unknown types.

---

## SHA256 cache

File hashes cached in `.wiki-cache/`. Unchanged files skip extraction on re-runs. Delete the cache to force full re-extraction.
