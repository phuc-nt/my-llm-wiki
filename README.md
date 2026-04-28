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

`my-llm-wiki` implements all three layers.

```bash
pip install my-llm-wiki
cd your-project && llm-wiki .
```

The output `wiki-out/vault/` is a drop-in Obsidian vault — open it directly, or query from CLI. Re-run anytime; SHA256 cache skips unchanged files. `llm-wiki note "<insight>"` writes back from your Claude Code sessions so the graph compounds over time.

### Read the docs

The full story lives at **[phuc-nt.github.io/my-llm-wiki](https://phuc-nt.github.io/my-llm-wiki/)**:

- **[How It's Built](https://phuc-nt.github.io/my-llm-wiki/why.html)** — narrative: Karpathy's vision → three layers → the living wiki cycle
- **[Install & Quick Start](https://phuc-nt.github.io/my-llm-wiki/quick-start.html)** — first graph in 30 seconds
- **[Core Features](https://phuc-nt.github.io/my-llm-wiki/core-features.html)** — two-pass extraction, typed inheritance, doc comments, communities, write-back
- **[How It Works](https://phuc-nt.github.io/my-llm-wiki/how-it-works.html)** — pipeline internals
- **[Use Cases](https://phuc-nt.github.io/my-llm-wiki/use-cases.html)** — codebases, research notes, mixed knowledge

### License

[MIT](LICENSE)
