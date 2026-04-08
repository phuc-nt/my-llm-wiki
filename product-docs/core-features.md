---
layout: default
title: Core Features
nav_order: 4
description: "Extraction quality, community detection, querying, watcher, ingest, schema."
---

# Core Features

## Extraction quality by file type

| File Type | Structural (free) | + Agent (semantic) | Verdict |
|-----------|-------------------|-------------------|---------|
| Code (18 languages) | Full AST | — | No agent needed |
| Markdown/text | Headings + links | 2x entities | Optional |
| DOCX | Hub nodes only | **30x entities** | Use agent |
| Scanned PDF | 0 text | **85x entities** | Use agent |
| Images (HEIC, PNG, JPG) | Hub nodes only | **Vision OCR** | Use agent |

See [How It Works]({% link how-it-works.md %}) for extraction flow details.

---

## Community detection

Leiden/Louvain groups related nodes. No embeddings — pure graph topology.

- Adaptive resolution: dense code graphs get tight communities, sparse doc graphs get broader grouping
- Semantic labels from top-degree nodes
- Cohesion scores measure internal edge density
- Oversized communities auto-split (> 15% of graph)

---

## Query commands

```bash
llm-wiki query search <terms>       # keyword search
llm-wiki query node <label>         # node details + source location
llm-wiki query neighbors <label>    # direct connections with edge types
llm-wiki query community <id>       # community members by degree
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
llm-wiki add https://example.com                        # fetch as markdown
llm-wiki add https://arxiv.org/pdf/... --author "Name"  # with metadata
```

Saved to `wiki-out/ingested/` with YAML frontmatter. Next `llm-wiki .` includes it.

---

## Schema rules

Create `.wikischema` to define custom entity and relation types:

```json
{
  "entity_types": ["code", "document", "paper", "image", "concept"],
  "relation_types": ["imports", "calls", "references", "explains", "contradicts"]
}
```

Graph validation warns about unknown types.

---

## SHA256 cache

File hashes in `.wiki-cache/`. Unchanged files skip extraction on re-runs.
