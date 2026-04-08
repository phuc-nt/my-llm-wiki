---
layout: default
title: Home
nav_order: 1
description: "my-llm-wiki — Turn any folder into a queryable knowledge graph."
permalink: /
---

# my-llm-wiki
{: .fs-9 }

Turn any folder of code, docs, papers, or images into a queryable knowledge graph.
{: .fs-6 .fw-300 }

[Get Started]({% link quick-start.md %}){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[Why LLM Wiki]({% link why.md %}){: .btn .fs-5 .mb-4 .mb-md-0 }

---

In April 2026, Andrej Karpathy shared a concept he called **LLM Wiki** — a personal knowledge system where you drop raw files into a folder and compile them into a structured, interlinked wiki.

The core insight: **compile once, query forever.**

`my-llm-wiki` brings this to life with a single command. No vector databases, no RAG pipelines, no API keys needed for code extraction.

---

### How it works

```
your-files/ → detect → extract → cross-ref → build → cluster → export
```

| Pass | What | Cost |
|------|------|------|
| **Structural** | AST for code (18 languages), headings/links for docs | Free |
| **Semantic** | Claude Code agents read DOCX, scanned PDFs, images | Claude tokens |

---

### What you get

| Output | Description |
|--------|-------------|
| `graph.html` | Interactive graph — click, search, filter by community |
| `graph.json` | Persistent graph — query weeks later without re-reading files |
| `WIKI_REPORT.md` | God nodes, surprising connections, knowledge gaps |
| `wiki/` | Wikipedia-style articles per community |
| `vault/` | Markdown vault with `[[wikilinks]]` |
