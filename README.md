<p align="center">
  <img src="assets/logo.svg" width="120" alt="my-llm-wiki logo" />
</p>

<h1 align="center">my-llm-wiki</h1>

<p align="center">
  Turn any folder of code into a queryable knowledge graph.
</p>

---

Inspired by [Andrej Karpathy's LLM Wiki concept](https://x.com/karpathy/status/1909380524543902036): drop raw files → compile once → query forever. No vector databases, no RAG. Just a graph.

## Install

```bash
pip install my-llm-wiki

# Optional extras
pip install my-llm-wiki[all]   # PDF + .docx/.xlsx + Leiden clustering
```

## Build

```bash
llm-wiki .                  # scan current folder
llm-wiki /path/to/project   # scan specific folder
```

Output goes to `wiki-out/`.

## Query

Once built, query without re-reading source files:

```bash
llm-wiki query search GraphStore        # keyword search
llm-wiki query node GraphStore           # node details + source location
llm-wiki query neighbors GraphStore      # direct connections
llm-wiki query community 0              # list community members
llm-wiki query path GraphStore Settings  # shortest path between concepts
llm-wiki query gods                      # most connected nodes
llm-wiki query stats                     # summary statistics
```

## Watch & Ingest

```bash
llm-wiki watch .              # auto-rebuild on file changes
llm-wiki watch . 10           # poll every 10 seconds
llm-wiki add https://url.com  # fetch URL, save as markdown, rebuild later
```

## Outputs

| File | What |
|------|------|
| `graph.html` | Interactive graph — click, search, filter by community |
| `graph.json` | Persistent graph data — query weeks later |
| `WIKI_REPORT.md` | God nodes, surprising connections, knowledge gaps |
| `wiki/` | Wikipedia-style articles per community |
| `vault/` | Markdown vault with `[[wikilinks]]` and YAML frontmatter |

## How It Works

```
your-files/ → detect → extract → build → cluster → analyze → export
```

- **detect** — scan for code, docs, papers. Respects `.wikiignore`
- **extract** — parse via tree-sitter AST (18 languages). No LLM needed
- **build** — assemble NetworkX knowledge graph
- **cluster** — find communities via Leiden/Louvain
- **analyze** — god nodes, surprising connections, suggested questions
- **export** — JSON + HTML + wiki + vault

### Supported Languages

Python · JavaScript · TypeScript · Go · Rust · Java · C · C++ · Ruby · C# · Kotlin · Scala · PHP · Swift · Lua · Zig · PowerShell · Elixir

## Claude Code Integration

Let Claude query your codebase graph directly as a skill:

```bash
# Copy the bundled skill into Claude Code
mkdir -p ~/.claude/skills/my-llm-wiki
cp "$(python -c 'import my_llm_wiki; print(my_llm_wiki.__path__[0])')/SKILL.md" ~/.claude/skills/my-llm-wiki/
```

After setup, Claude can use `llm-wiki query` commands to answer questions about your codebase structure.

## Roadmap

Karpathy's LLM Wiki has 3 layers: **Raw → Compile → Query**

| Layer | Feature | Status |
|-------|---------|--------|
| **Raw** | Scan code, docs, papers, images | ✅ Done |
| **Raw** | `.wikiignore` + SHA256 cache | ✅ Done |
| **Compile** | AST extraction (18 languages) | ✅ Done |
| **Compile** | Community detection + labeling | ✅ Done |
| **Compile** | Structural extraction for docs/papers | ✅ Done |
| **Compile** | LLM semantic extraction (agent mode) | ✅ Done |
| **Compile** | Cross-reference code ↔ docs | ✅ Done |
| **Compile** | User-defined schema rules (`.wikischema`) | ✅ Done |
| **Query** | CLI query (search, path, neighbors) | ✅ Done |
| **Query** | Claude Code skill integration | ✅ Done |
| **Query** | File watcher (`llm-wiki watch`) | ✅ Done |
| **Query** | URL ingest (`llm-wiki add <url>`) | ✅ Done |

## License

[MIT](LICENSE)
