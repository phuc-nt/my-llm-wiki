---
layout: default
title: Why LLM Wiki
nav_order: 2
description: "Why knowledge graphs beat RAG at personal scale, and how the living wiki pattern works."
---

# Why LLM Wiki

## The problem

You have code, docs, papers, screenshots. You want to ask questions about them.

| Approach | Issue |
|----------|-------|
| Paste into chat | Hits context limits, no persistence |
| RAG pipeline | Complex setup, vector DB, chunking, embedding model |
| Full re-read | Expensive, slow, no cross-document connections |

None compile knowledge once and let you query forever.

---

## Karpathy's three layers

> *"A large fraction of my recent token throughput has gone not into manipulating code, but into manipulating knowledge."*

1. **Raw** — your files, never modified
2. **Compile** — structured knowledge with cross-references
3. **Query** — ask questions without re-reading source files

**Compilation is separate from querying.** Build the graph once, query for weeks.

---

## Graphs vs. embeddings

| | Vector DB (RAG) | Knowledge Graph |
|---|---|---|
| Setup | Embedding model + chunking + DB | `pip install my-llm-wiki` |
| Cross-references | Chunks are isolated | Edges connect everything |
| Structure | Flat similarity | Communities, paths, hubs |
| Explainability | "These chunks are similar" | "A calls B which imports C" |
| Persistence | Running DB | JSON file on disk |
| Cost | Embedding API calls | Free (AST) or one-time (agent) |

At personal scale (10-1000 files), you don't need approximate nearest neighbor. You need **what connects to what**.

---

## The living wiki

Karpathy's vision goes beyond "compile once" — the wiki is a **persistent, compounding artifact**. Every session adds knowledge. Insights get filed back. The graph grows over time.

```
Monitor → Rebuild → Lint → Write-back → Report
   ↑                                       │
   └───────────────────────────────────────┘
```

- **Monitor** — detect file changes, trigger rebuild
- **Rebuild** — SHA256 cache skips unchanged files
- **Lint** — find orphans, tiny communities, high ambiguity
- **Write-back** — file insights as markdown, merge into graph
- **Report** — track growth: nodes, edges, communities over time

This cycle is implemented in the Claude Code skill. The agent follows it automatically when you run `/wiki .`.

---

## Three confidence levels

Every edge is tagged:

- **EXTRACTED** — found directly in source (import, link, citation)
- **INFERRED** — reasoned by extractor (shared concept, implied dependency)
- **AMBIGUOUS** — uncertain, flagged for review

You always know what was found vs. guessed.
