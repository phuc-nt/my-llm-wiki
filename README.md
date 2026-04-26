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
pip install my-llm-wiki              # core: code + markdown
pip install 'my-llm-wiki[docling]'   # + layout-aware PDF/DOCX/PPTX/HTML extraction
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
| **Structural** | AST (18 languages): classes, functions, typed `extends`/`implements` edges, function signatures, doc comments (Javadoc/JSDoc/GoDoc), call graph, headings, cross-ref. Layout-aware extraction for PDF/DOCX/PPTX/HTML via Docling, with OCR fallback for scanned PDFs. | Free |
| **Semantic** | Claude Code agents read images with vision; deeper synthesis on any file | Claude tokens |

Output goes to `wiki-out/`:

```
wiki-out/
  graph.html       ← interactive graph (vis.js)
  graph.json       ← persistent graph data
  WIKI_REPORT.md   ← god nodes, surprising connections
  wiki/            ← Wikipedia-style articles
  vault/           ← Obsidian vault — index.md catalog + [[wikilinks]] + YAML frontmatter
  cache/           ← SHA256 cache (skip unchanged files)
```

### Obsidian integration

`wiki-out/vault/` is a drop-in Obsidian vault. Open it directly, or symlink into an existing vault:

```bash
llm-wiki .
# Obsidian → Open folder as vault → wiki-out/vault/
```

You get: graph view (force-directed), backlinks, tag pane, full-text search, and Properties view (Obsidian 1.4+ reads the YAML frontmatter on each node). Community colors are pre-configured via `.vault/graph.json`. Use `llm-wiki query` from CLI for typed-edge details (Obsidian wikilinks are untyped, so `extends`/`implements`/`calls` collapse to generic links in the Obsidian graph view).

Node notes are organized into `code/`, `document/`, `paper/`, `image/`, `note/`, and `other/` subfolders so the vault stays navigable as it grows. Community summaries live in `communities/`. Wikilinks remain basename-only — Obsidian resolves them across the vault regardless of folder.

**`vault/index.md`** is the entry point — content catalog grouped by file type with a Communities section. LLMs (and humans) read it first to navigate the vault before drilling into specific notes.

**`vault/log.md`** is the append-only activity log — chronological record of every build and note write-back. Grep-friendly format for auditing how the wiki has grown over time.

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
