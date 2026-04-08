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

```bash
pip install my-llm-wiki
llm-wiki .
```

---

### What you get

```
wiki-out/
  graph.html       ← interactive graph (vis.js)
  graph.json       ← persistent graph data
  WIKI_REPORT.md   ← god nodes, surprising connections
  wiki/            ← Wikipedia-style articles
  vault/           ← markdown vault with [[wikilinks]]
```

See [How It Works]({% link how-it-works.md %}) for the full pipeline architecture.
