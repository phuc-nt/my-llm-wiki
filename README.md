<p align="center">
  <img src="assets/logo.svg" width="120" alt="my-llm-wiki logo" />
</p>

<h1 align="center">my-llm-wiki</h1>

<p align="center">
  Drop any files into a folder. Get a living, queryable knowledge graph.
</p>

<p align="center">
  <a href="https://pypi.org/project/my-llm-wiki/"><img src="https://img.shields.io/pypi/v/my-llm-wiki" alt="PyPI"></a>
  <a href="https://phuc-nt.github.io/my-llm-wiki/">Documentation</a> ·
  <a href="https://github.com/phuc-nt/my-llm-wiki/issues">Issues</a>
</p>

---

In April 2026, Andrej Karpathy [shared a concept](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) he called **LLM Wiki** — a personal knowledge system with three layers: raw files (never modified), a compiled wiki with cross-references, and a schema that tells the LLM how to maintain it. The key insight: **compile once, query forever**, and let the wiki grow with every session as a "persistent, compounding artifact" rather than re-deriving knowledge on every query.

`my-llm-wiki` implements all three layers. See [How It's Built](https://phuc-nt.github.io/my-llm-wiki/why.html) for the full narrative on how Karpathy's vision is realized.

```bash
pip install my-llm-wiki
cd your-project && llm-wiki .
```

### The Living Wiki

One command builds the graph. The living wiki cycle keeps it growing over time — each session adds knowledge, insights get filed back, the graph compounds.

```
┌──────────────────────────────────────────────────┐
│                                                  │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│   │ Monitor  │───▶│ Rebuild  │───▶│  Lint    │  │
│   │ (watch)  │    │ (cached) │    │ (health) │  │
│   └──────────┘    └──────────┘    └──────────┘  │
│        ▲                               │         │
│        │                               ▼         │
│   ┌──────────┐                  ┌──────────┐    │
│   │  Report  │◀─────────────────│Write-back│    │
│   │ (stats)  │                  │(insights)│    │
│   └──────────┘                  └──────────┘    │
│                                                  │
└──────────────────────────────────────────────────┘
```

Two passes extract knowledge from any file type:

| Pass | What | Cost |
|------|------|------|
| **Structural** | AST (18 languages): classes, functions, typed `extends`/`implements` edges, function signatures, doc comments (Javadoc/JSDoc/GoDoc), call graph, headings, cross-ref | Free |
| **Semantic** | Claude Code agents read DOCX, scanned PDFs, images with vision | Claude tokens |

Output goes to `wiki-out/`:

```
wiki-out/
  graph.html       ← interactive graph (vis.js)
  graph.json       ← persistent graph data
  WIKI_REPORT.md   ← god nodes, surprising connections
  wiki/            ← Wikipedia-style articles
  vault/           ← markdown vault with [[wikilinks]]
  cache/           ← SHA256 cache (skip unchanged files)
```

### CLI

```bash
llm-wiki .                          # build graph
llm-wiki query gods                 # most connected nodes
llm-wiki query search <term>        # keyword search
llm-wiki query path <A> <B>         # shortest path
llm-wiki lint                       # graph health check
llm-wiki watch .                    # auto-rebuild on changes
llm-wiki add <url>                  # ingest URL
llm-wiki note "<insight>"           # write-back from LLM session
```

### Claude Code Skill

```bash
mkdir -p ~/.claude/skills/my-llm-wiki
cp "$(python -c 'import my_llm_wiki; print(my_llm_wiki.__path__[0])')/SKILL.md" ~/.claude/skills/my-llm-wiki/
```

Then `/wiki .` in Claude Code — structural extraction + agent-mode semantic extraction for DOCX, scanned PDFs, images.

### Docs

**[phuc-nt.github.io/my-llm-wiki](https://phuc-nt.github.io/my-llm-wiki/)**

### License

[MIT](LICENSE)
