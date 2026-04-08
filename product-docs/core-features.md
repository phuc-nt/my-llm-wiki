---
layout: default
title: Core Features
nav_order: 4
description: "Two-pass extraction, doc comments, cross-referencing, community detection, querying, and the living wiki cycle."
---

# Core Features

## Two-pass extraction

### Pass 1 — Structural (free, deterministic)

Runs with `llm-wiki .`:

- **Code** (18 languages) — tree-sitter AST + doc comments (Javadoc, JSDoc, GoDoc, `///`)
- **Markdown/text** — headings, definitions, cross-document links
- **DOCX/PDF** — converted to text, then parsed
- **Images** — hub nodes (content needs agent mode)
- **Cross-reference** — code entities mentioned in docs get `mentions` edges

### Pass 2 — Semantic (agent mode)

Runs in Claude Code via `/wiki .`. Dispatches subagents for files structural can't handle:

| File Type | Structural | + Agent | Verdict |
|-----------|-----------|---------|---------|
| Code (18 langs) | Full AST + doc comments | — | No agent needed |
| Markdown | Headings + links | 2x entities | Optional |
| DOCX | Hub nodes only | **30x entities** | Use agent |
| Scanned PDF | 0 text | **85x entities** | Use agent |
| Images (HEIC/PNG/JPG) | Hub nodes only | **Vision OCR** | Use agent |

### Doc comment extraction

Automatically extracts business logic from inline documentation:

| Language | Format | Example |
|----------|--------|---------|
| Java, Kotlin, Scala, PHP | `/** ... */` | Javadoc |
| JavaScript, TypeScript | `/** ... */` | JSDoc |
| Go | `// ...` before func/type | GoDoc |
| Rust | `///` | Doc comments |
| C# | `///` | XML docs |
| Swift, Ruby | `///`, `#` | Doc comments |

Tested: 1,773 / 12,424 nodes enriched with Javadoc descriptions on a Java codebase.

---

## Community detection

Leiden/Louvain groups related nodes. No embeddings — pure graph topology.

- Adaptive resolution: tight for small codebases, broad for >5K nodes
- Semantic labels from top-degree nodes
- Cohesion scores
- Oversized communities auto-split

---

## Cross-reference code ↔ docs

Automatic `mentions` edges when a code entity name appears in doc text. Tested: 460 code↔doc edges on a mixed Python repo.

---

## SHA256 cache

File hashes in `wiki-out/cache/`. Unchanged files skip extraction on re-runs. Large codebases (1,000+ files) benefit significantly on second build.

---

## CLI

```bash
llm-wiki .                          # build graph
llm-wiki query search <terms>       # keyword search
llm-wiki query node <label>         # node details + doc comment
llm-wiki query neighbors <label>    # direct connections
llm-wiki query community <id>       # community members by degree
llm-wiki query path <A> <B>         # shortest path
llm-wiki query gods                 # top 10 most connected
llm-wiki query stats                # summary
llm-wiki lint                       # health check
llm-wiki watch .                    # auto-rebuild on changes
llm-wiki add <url>                  # fetch URL as markdown
llm-wiki --no-viz .                 # skip HTML for large graphs
llm-wiki --version                  # show version
```

---

## Schema rules

Create `.wikischema` for custom entity and relation types:

```json
{
  "entity_types": ["code", "document", "paper", "image", "concept"],
  "relation_types": ["imports", "calls", "references", "explains"]
}
```
