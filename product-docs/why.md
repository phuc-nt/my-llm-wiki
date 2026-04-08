---
layout: default
title: Why LLM Wiki
nav_order: 2
description: "Why knowledge graphs beat RAG and vector databases at personal scale."
---

# Why LLM Wiki

## The problem

You have a codebase, papers, docs, screenshots. You want to ask questions about them.

- **Paste into chat** — hits context limits, no persistence
- **RAG pipeline** — complex setup, vector DB, chunking, embedding model
- **Full re-read** — expensive, slow, no cross-document connections

None of these compile knowledge once and let you query forever.

---

## Karpathy's insight

> *"A large fraction of my recent token throughput has gone not into manipulating code, but into manipulating knowledge."*

Three layers:

1. **Raw** — your original files, never modified
2. **Compile** — structured knowledge with cross-references
3. **Query** — ask questions without re-reading source files

The key: **compilation is separate from querying.**

---

## Graphs vs. embeddings at personal scale

| | Vector DB (RAG) | Knowledge Graph |
|---|---|---|
| Setup | Embedding model + chunking + DB | `pip install my-llm-wiki` |
| Cross-references | No — chunks are isolated | Edges connect everything |
| Structure | Flat similarity | Communities, paths, hubs |
| Explainability | "These chunks are similar" | "A calls B which imports C" |
| Persistence | Running DB | JSON file on disk |
| Cost | Embedding API calls | Free (AST) or one-time (agent) |

At personal scale (10-1000 files), you don't need approximate nearest neighbor. You need to see **what connects to what**.

---

## Three confidence levels

Every edge is tagged:

- **EXTRACTED** — found directly in source (import, link, citation)
- **INFERRED** — reasoned by extractor (shared data, implied dependency)
- **AMBIGUOUS** — uncertain, flagged for review

You always know what was found vs. guessed.
