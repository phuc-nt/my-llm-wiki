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

Inspired by [Andrej Karpathy's LLM Wiki concept](https://x.com/karpathy/status/1909380524543902036): **compile once, query forever.** The wiki grows with every session.

```bash
pip install my-llm-wiki
cd your-project && llm-wiki .
```

### What it does

```
your-files/ → detect → extract → cross-ref → build → cluster → export
                                                        ↓
                                              wiki-out/graph.html
                                              wiki-out/graph.json
                                              wiki-out/WIKI_REPORT.md
                                              wiki-out/wiki/
                                              wiki-out/vault/
```

### Two-pass extraction

| Pass | What | Cost |
|------|------|------|
| **Structural** | AST (18 languages), doc comments (Javadoc/JSDoc/GoDoc), headings, cross-ref | Free |
| **Semantic** | Claude Code agents read DOCX, scanned PDFs, images with vision | Claude tokens |

### CLI

```bash
llm-wiki .                          # build graph
llm-wiki query gods                 # most connected nodes
llm-wiki query search <term>        # keyword search
llm-wiki query path <A> <B>         # shortest path
llm-wiki lint                       # graph health check
llm-wiki watch .                    # auto-rebuild on changes
llm-wiki add <url>                  # ingest URL
```

### Living Wiki

The graph is a persistent, compounding artifact — it grows with every session:

```
Monitor → Rebuild → Lint → Write-back → Report
   ↑                                       │
   └───────────────────────────────────────┘
```

### Claude Code Skill

```bash
mkdir -p ~/.claude/skills/my-llm-wiki
cp "$(python -c 'import my_llm_wiki; print(my_llm_wiki.__path__[0])')/SKILL.md" ~/.claude/skills/my-llm-wiki/
```

Then `/wiki .` — structural extraction + agent-mode semantic extraction for DOCX, scanned PDFs, images.

### Docs

**[phuc-nt.github.io/my-llm-wiki](https://phuc-nt.github.io/my-llm-wiki/)**

### License

[MIT](LICENSE)
