---
layout: default
title: Core Features
nav_order: 4
description: "Two-pass extraction, doc comments, cross-referencing, community detection, querying, and the living wiki cycle."
---

# Core Features

## Two-pass extraction

### Pass 1 — Structural (free, deterministic)

Runs with `llm-wiki .`:

- **Code** (19 languages) — tree-sitter AST with rich metadata:
  - Classes, functions, methods, imports
  - **Typed inheritance edges**: `extends` (base class) and `implements` (interface)
  - **Function signatures**: parameters + return types preserved verbatim
  - Doc comments (Javadoc, JSDoc, GoDoc, `///`)
  - Call graph (function-to-function calls)
- **Markdown/text** — headings, definitions, cross-document links
- **PDF/DOCX/PPTX/HTML/EPUB** — layout-aware extraction via [Docling](https://github.com/docling-project/docling) (install `[docling]` extra). Headings, tables, and structure preserved. Scanned PDFs auto-detected and re-run with OCR. EPUB unpacked via stdlib zipfile and routed through Docling's HTML pipeline. PDF hub nodes carry a `pages` attribute. Documents using inline `**bold**` instead of heading styles are still sectioned via a fallback heuristic.
- **Images** — hub nodes (content needs agent mode)
- **Cross-reference** — code entities mentioned in docs get `mentions` edges

### Pass 2 — Semantic (agent mode)

Runs in Claude Code via `/wiki .`. Dispatches subagents for deeper synthesis on any file:

| File Type | Structural | + Agent | Verdict |
|-----------|-----------|---------|---------|
| Code (19 langs) | Full AST + doc comments | — | No agent needed |
| Markdown | Headings + links | 2x entities | Optional |
| DOCX/PPTX/HTML/EPUB | Layout-aware extraction (Docling) | Deeper synthesis | Optional |
| PDF (text) | Layout + page count (Docling) | Deeper synthesis | Optional |
| PDF (scanned) | OCR fallback (Docling) | Deeper synthesis | Optional |
| Images (HEIC/PNG/JPG) | Hub nodes only | **Vision OCR** | Use agent |

### Typed inheritance edges

Instead of a single generic `inherits` relation, the graph distinguishes:

- **`extends`** — class inherits from a base class
- **`implements`** — class conforms to an interface/protocol/trait

Languages supported for typed inheritance:

| Language | `extends` | `implements` | Notes |
|----------|-----------|-------------|-------|
| Java | ✅ | ✅ | First-class grammar support |
| Python | ✅ | — | Single concept, handles `Generic[T]` |
| TypeScript | ✅ | ✅ | Separate `extends`/`implements` clauses |
| Kotlin | ✅ | — | `:` delegation_specifiers |
| C# | ✅ | ✅ | First entry = extends, rest = implements |
| C++ | ✅ | — | `: public Base` |
| Ruby | ✅ | — | `< Base` (mixins need agent mode) |
| PHP | ✅ | ✅ | Separate clauses |
| Scala | ✅ | ✅ | First = extends, `with Trait` = implements |
| Swift | ✅ | — | Class base + protocol conformance merged |

Query: `llm-wiki query neighbors Serializable` → shows all classes implementing it.

---

### Function signatures

Every function/method node carries a `signature` field with params and return type:

```
llm-wiki query node processOrder
  processOrder()
    source: src/orders.ts L45
    type: code  community: 3  degree: 8
    signature: (order: Order, user: User): Promise<Result>
    doc: Process an order for the given user. Returns result or throws.
```

Signature extraction supports: Python, TypeScript, JavaScript, Java, Kotlin, C#, C++, Ruby, PHP, Scala, Swift. Works with generic parameters, default values, nullable types.

Test result on Python codebase (kioku): **529 / 991 code nodes have signatures** (54% coverage — classes and untyped functions have no signature).

---

### Doc comment extraction

Automatically extracts business logic from inline documentation:

| Language | Format | Example |
|----------|--------|---------|
| Java, Kotlin, Scala, PHP | `/** ... */` | Javadoc |
| JavaScript, TypeScript | `/** ... */` | JSDoc |
| Go | `// ...` before func/type | GoDoc |
| Rust | `///` | Doc comments |
| C# | `///` | XML docs |
| Swift, Ruby | `///`, `#` | Doc comments |

Tested: 1,773 / 12,424 nodes enriched with Javadoc descriptions on a Java codebase.

---

## Community detection

Leiden/Louvain groups related nodes. No embeddings — pure graph topology.

- Adaptive resolution: tight for small codebases, broad for >5K nodes
- Semantic labels from top-degree nodes
- Cohesion scores
- Oversized communities auto-split

---

## Cross-reference code ↔ docs

Automatic `mentions` edges when a code entity name appears in doc text. Tested: 460 code↔doc edges on a mixed Python repo.

---

## SHA256 cache

File hashes in `wiki-out/cache/`. Unchanged files skip extraction on re-runs. Large codebases (1,000+ files) benefit significantly on second build.

---

## CLI

```bash
llm-wiki .                          # build graph
llm-wiki query search <terms>       # keyword search
llm-wiki query node <label>         # node details + doc comment
llm-wiki query neighbors <label>    # direct connections
llm-wiki query community <id>       # community members by degree
llm-wiki query path <A> <B>         # shortest path
llm-wiki query gods                 # top 10 most connected
llm-wiki query stats                # summary
llm-wiki lint                       # health check
llm-wiki watch .                    # auto-rebuild on changes
llm-wiki add <url>                  # fetch URL as markdown
llm-wiki note "<insight>" [--link <node>] [--tag <tag>]   # write-back insight
llm-wiki --no-viz .                 # skip HTML for large graphs
llm-wiki --version                  # show version
```

---

## Write-back from LLM sessions

Karpathy's vision is a **compounding artifact** — the wiki grows with every session. `llm-wiki note` closes the loop:

```bash
llm-wiki note "GraphStore uses SHA256 because cache needs stable hash across runs" \
    --link GraphStore --tag rationale
```

The note is saved to `wiki-out/ingested/note-<timestamp>-<slug>.md` with YAML frontmatter (type, date, tags, links). On the next `llm-wiki .` rebuild:

1. The note file is picked up like any other markdown
2. `[[WikiLinks]]` in the body become `mentions` edges to existing nodes
3. The insight is searchable via `llm-wiki query search <term>`

**Claude Code integration**: SKILL.md instructs agents to call `llm-wiki note` proactively when they explain non-obvious rationale, make architectural decisions, or discover hidden constraints. One insight per note, written as *why* not *what*. See SKILL.md → Write-back section for the full heuristics.

---

## Obsidian compatibility

`wiki-out/vault/` is a drop-in Obsidian vault. Each node becomes one markdown file with:

- **`index.md`** — auto-generated content catalog grouped by file type with a Communities section. The entry point LLMs read first to navigate the vault efficiently
- **`log.md`** — append-only chronological record of vault activity (builds, note write-backs). Format: `## [YYYY-MM-DD HH:MM] [op] | desc`. Grep-friendly audit trail for the compounding-artifact loop
- **Subfolders by type** — `code/`, `document/`, `paper/`, `image/`, `note/`, `other/` for nodes; `communities/` for community summaries. Wikilinks remain basename-only so Obsidian resolves them across the vault
- **`[[WikiLinks]]`** for every graph edge — Obsidian backlinks work immediately
- **YAML frontmatter** with `id`, `type`, `community`, `degree`, `source_file` — renders as Obsidian Properties (1.4+)
- **Inline `#tags`** from community labels — appear in Obsidian's tag pane
- **Pre-configured graph colors** via `.vault/graph.json` — community coloring matches the vis.js graph

```bash
llm-wiki .
# Obsidian → Open folder as vault → select wiki-out/vault/
```

**Trade-off:** Obsidian wikilinks are untyped, so `extends` / `implements` / `calls` / `mentions` all render as generic links in Obsidian's graph view. Use `llm-wiki query neighbors <label>` from the CLI for typed-edge detail.

---

## Schema rules

Create `.wikischema` for custom entity and relation types:

```json
{
  "entity_types": ["code", "document", "paper", "image", "concept"],
  "relation_types": ["imports", "calls", "references", "explains"]
}
```
