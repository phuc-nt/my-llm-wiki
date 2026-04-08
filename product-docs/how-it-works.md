---
layout: default
title: How It Works
nav_order: 3
description: "Pipeline architecture, extraction flows, and graph construction explained with diagrams."
---

# How It Works

## Pipeline overview

```
┌──────────────────────────────────────────────────────────────────┐
│                         your-files/                              │
│  *.py *.ts *.go    *.md *.txt    *.pdf *.docx    *.png *.heic   │
└──────────┬──────────────┬────────────┬──────────────┬────────────┘
           │              │            │              │
           ▼              ▼            ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────────┐
│   detect     │ │   detect     │ │  detect  │ │   detect     │
│  → code      │ │  → document  │ │  → paper │ │  → image     │
└──────┬───────┘ └──────┬───────┘ └────┬─────┘ └──────┬───────┘
       │                │              │               │
       ▼                ▼              ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────────┐
│  AST extract │ │  structural  │ │ pypdf →  │ │  hub nodes   │
│  (tree-sitter│ │  (headings,  │ │ structural│ │  (file refs) │
│  18 languages│ │  links, defs)│ │ or hub   │ │              │
└──────┬───────┘ └──────┬───────┘ └────┬─────┘ └──────┬───────┘
       │                │              │               │
       └────────────────┴──────┬───────┴───────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  cross-reference    │
                    │  code ↔ docs        │
                    │  (mentions edges)   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  build graph        │
                    │  (NetworkX)         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  cluster            │
                    │  (Leiden/Louvain)   │
                    └──────────┬──────────┘
                               │
                               ▼
                ┌──────────────┴───────────────┐
                │           export             │
                ├──────────┬──────────┬────────┤
                │graph.html│graph.json│report  │
                │graph.html│wiki/     │vault/  │
                └──────────┴──────────┴────────┘
```

---

## Step 1 — Detect

Scans folder recursively. Classifies files by type. Respects `.wikiignore`.

```
detect(root)
  │
  ├── skip: .git, node_modules, __pycache__, wiki-out/
  ├── skip: .env, *.pem, credentials (sensitive files)
  │
  ├── .py .ts .go .rs .java ... → code
  ├── .md .txt .rst             → document
  ├── .pdf                      → paper (or document if no academic signals)
  ├── .docx .xlsx               → document (converted to markdown)
  ├── .png .jpg .heic .svg      → image
  │
  └── output: {files: {code: [...], document: [...], paper: [...], image: [...]},
               total_files, total_words}
```

---

## Step 2 — Extract

### Code extraction (AST)

```
source.py
  │
  ├── tree-sitter parse → AST
  │
  ├── walk AST nodes:
  │     class Foo        → node(id, label="Foo", file_type="code")
  │     def bar()        → node(id, label="bar()", file_type="code")
  │     import X         → edge(source→X, relation="imports")
  │     class Foo(Base)  → edge(Foo→Base, relation="inherits")
  │
  ├── cross-file imports:
  │     from mod import A → edge(A→A_in_mod, relation="imports_from")
  │
  └── output: {nodes: [...], edges: [...]}
```

### Document extraction (structural)

```
document.md
  │
  ├── # Heading 1          → section node (h1/h2 only)
  ├── ## Heading 2          → section node, edge(h1→h2, "contains")
  │
  ├── - **Term**: desc      → definition node, edge(doc→term, "defines")
  │     (skip terms with special chars, >40 chars, inside code blocks)
  │
  ├── [link](other.md)      → edge(doc→other, "references")
  │     (deduplicated, normalized paths)
  │
  └── cross-doc: same label in different files → edge("same_concept", INFERRED)
```

### Image & scanned PDF extraction

```
image.heic / scanned.pdf
  │
  ├── structural: hub node only (filename as label)
  │     (no text extractable — pypdf returns empty for scanned pages)
  │
  └── agent mode (Step 2 in SKILL.md):
        Claude reads file with vision → extracts entities → JSON
        people, places, concepts, text (OCR), relationships
```

---

## Step 3 — Cross-reference

Runs when both code AND docs exist. Links code entities mentioned in doc text.

```
README.md text: "The GraphStore class handles all persistence..."
                          │
                          ▼
            pattern match: "GraphStore" found
                          │
                          ▼
            edge(README → GraphStore, relation="mentions", INFERRED)
```

```
Code entities eligible for matching:
  ✓ class names (GraphStore, UserService)
  ✓ function names (detect, cluster)
  ✗ method stubs (.traverse(), .__init__())
  ✗ file-hub nodes (detect-files.py)
  ✗ labels < 3 chars
```

---

## Step 4 — Build graph

Merges all extraction results into a single NetworkX graph.

```
[code_result, doc_result, semantic_result]
  │
  ├── deduplicate nodes by ID
  ├── merge edges (preserve _src/_tgt for direction display)
  │
  └── output: nx.Graph with node/edge attributes
        node: {id, label, file_type, source_file, source_location}
        edge: {relation, confidence, source_file, _src, _tgt}
```

---

## Step 5 — Cluster

```
Graph (N nodes, E edges)
  │
  ├── density check:
  │     avg_degree ≤ 3      → resolution = 1.0 (broad, for docs)
  │     nodes > 5000        → resolution = 1.0 (fewer communities)
  │     otherwise           → resolution = 1.5 (tight, for code)
  │
  ├── Leiden (if graspologic installed) or Louvain (networkx builtin)
  │
  ├── split oversized communities (> 15% of graph, min 10 nodes)
  │
  ├── label each community from top-degree node names
  │
  └── score cohesion (internal edge density)
```

---

## Step 6 — Export

```
wiki-out/
  │
  ├── graph.json          ← node-link JSON, community assignments
  │                         queryable with llm-wiki query
  │
  ├── graph.html          ← vis.js interactive graph
  │                         nodes sized by degree, colored by community
  │
  ├── WIKI_REPORT.md      ← god nodes, surprising connections,
  │                         community summaries, suggested questions
  │
  ├── wiki/               ← one .md per community + god node articles
  │     index.md            cross-links, bridge nodes
  │     Community_0.md
  │     GraphStore.md
  │
  └── vault/              ← one .md per node with [[wikilinks]]
        .vault/graph.json   community color config
        GraphStore.md       YAML frontmatter + inline tags
        Settings.md
```

---

## Agent mode flow (semantic extraction)

When running `/wiki .` in Claude Code, the skill adds a second pass:

```
Step 1: llm-wiki .              ← structural (free)
  │
  ▼
Step 2: check output
  │
  ├── code-only graph, many edges → done, skip agent
  │
  ├── DOCX/PDF/images with 0 edges → dispatch agents:
  │
  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
  │   │  Agent 1    │  │  Agent 2    │  │  Agent 3    │
  │   │  read DOCX  │  │  read PDF   │  │  read images│
  │   │  extract    │  │  (vision)   │  │  (vision)   │
  │   │  entities   │  │  extract    │  │  OCR + desc │
  │   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
  │          │                │                │
  │          └────────────────┴────────────────┘
  │                           │
  │                    semantic.json
  │                           │
  ▼                           ▼
Step 3: merge structural + semantic → rebuild graph → re-export
```

---

## Doc comment extraction

Automatic enrichment of AST nodes with business logic from inline docs:

```
source.java
  │
  ├── /** Match YHC orders with delivery data.    ← Javadoc
  │    *  Uses 3-month sliding window.
  │    */
  ├── public class YhcOrderMatchingService {      ← AST node
  │
  └── Result:
        node.label = "YhcOrderMatchingService"
        node.description = "Match YHC orders with delivery data. Uses 3-month sliding window."
```

Supported: `/** */` (Java/JS/TS/PHP), `//` (Go), `///` (Rust/C#/Swift), `#` (Ruby)

---

## Living wiki cycle

After initial build, the wiki grows with every session:

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

Monitor:    llm-wiki watch .           or check mtime
Rebuild:    llm-wiki .                 SHA256 cache skips unchanged
Lint:       llm-wiki lint              orphans, tiny communities
Write-back: wiki-out/ingested/*.md     insights filed as markdown
Report:     llm-wiki query stats       track growth over time
```
