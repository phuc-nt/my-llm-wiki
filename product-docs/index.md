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

---

### v0.9 — Semantic vault maintenance & session capture

**Per-heading page citations:** PDFs, Word docs, and slides now track which page each heading came from (visible in vault YAML and CLI output).

**Session capture:** `llm-wiki capture` scans your Claude Code logs and extracts note candidates. Review them, promote to vault with `llm-wiki note`.

**Vault maintenance:** `/wiki maintain` agent runs semantic audits — detects orphans, broken links, contradictions, stale TODOs.

**New query helpers:** `llm-wiki query orphans` and `llm-wiki query stale-refs` power the audit workflow.

**CI matrix:** Tests on Linux, macOS, Windows × Python 3.10–3.13. Integration tests on Ubuntu + Python 3.13.
