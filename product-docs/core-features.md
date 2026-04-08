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

- **Code** (18 languages) — tree-sitter AST with rich metadata:
  - Classes, functions, methods, imports
  - **Typed inheritance edges**: `extends` (base class) and `implements` (interface)
  - **Function signatures**: parameters + return types preserved verbatim
  - Doc comments (Javadoc, JSDoc, GoDoc, `///`)
  - Call graph (function-to-function calls)
- **Markdown/text** — headings, definitions, cross-document links
- **DOCX/PDF** — converted to text, then parsed
- **Images** — hub nodes (content needs agent mode)
- **Cross-reference** — code entities mentioned in docs get `mentions` edges

### Pass 2 — Semantic (agent mode)

Runs in Claude Code via `/wiki .`. Dispatches subagents for files structural can't handle:

| File Type | Structural | + Agent | Verdict |
|-----------|-----------|---------|---------|
| Code (18 langs) | Full AST + doc comments | — | No agent needed |
| Markdown | Headings + links | 2x entities | Optional |
| DOCX | Hub nodes only | **30x entities** | Use agent |
| Scanned PDF | 0 text | **85x entities** | Use agent |
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
llm-wiki --no-viz .                 # skip HTML for large graphs
llm-wiki --version                  # show version
```

---

## Schema rules

Create `.wikischema` for custom entity and relation types:

```json
{
  "entity_types": ["code", "document", "paper", "image", "concept"],
  "relation_types": ["imports", "calls", "references", "explains"]
}
```
