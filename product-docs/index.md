---
layout: default
title: Home
nav_order: 1
description: "my-llm-wiki — A living, queryable knowledge graph from any folder."
permalink: /
---

# my-llm-wiki
{: .fs-9 }

Drop any files into a folder. Get a living, queryable knowledge graph.
{: .fs-6 .fw-300 }

[Get Started]({{ site.baseurl }}/quick-start.html){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[Why LLM Wiki]({{ site.baseurl }}/why.html){: .btn .fs-5 .mb-4 .mb-md-0 }

---

### The idea

In April 2026, Andrej Karpathy shared a concept he called **LLM Wiki** — a personal knowledge system with three layers:

1. **Raw** — your files, never modified
2. **Compile** — structured knowledge with cross-references
3. **Query** — ask questions without re-reading source files

The key insight: **compile once, query forever.** The wiki is a persistent, compounding artifact — it grows with every session.

`my-llm-wiki` implements all three layers. One command builds the graph. The living wiki cycle keeps it growing.

```bash
pip install my-llm-wiki
cd your-project && llm-wiki .
```

---

### The living wiki cycle

```
Monitor → Rebuild → Lint → Write-back → Report
   ↑                                       │
   └───────────────────────────────────────┘
```

Each session adds knowledge. Insights get filed back. The graph compounds over time — exactly what Karpathy envisioned.

---

### What you get

```
wiki-out/
  graph.html       ← interactive graph (vis.js)
  graph.json       ← persistent graph data
  WIKI_REPORT.md   ← god nodes, surprising connections
  wiki/            ← Wikipedia-style articles
  vault/           ← markdown vault with [[wikilinks]]
  cache/           ← SHA256 cache (skip unchanged files)
```

See [How It Works]({{ site.baseurl }}/how-it-works.html) for the full pipeline architecture.
