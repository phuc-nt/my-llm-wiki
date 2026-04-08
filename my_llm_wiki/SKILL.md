# my-llm-wiki

Turn any folder of code, docs, papers, or images into a queryable knowledge graph.

Drop raw files → compile once → query forever. The wiki grows with every session.

---

## When `/wiki` is Invoked

If no path given, use `.` (current directory).

### Step 1 — Structural extraction (free, fast)

```bash
llm-wiki .
```

Read the summary output. Note file counts and edge counts per type.

- **Code** → full AST + doc comments (Javadoc, JSDoc, GoDoc, `///`). No agent needed.
- **Markdown/text** → headings, definitions, cross-doc links. Usually sufficient.
- **DOCX, scanned PDFs, images** → hub nodes only. Proceed to Step 2.

### Step 2 — Semantic extraction (agent mode)

Skip if Step 1 produced a rich graph (code-only repos, markdown with many edges).

Group non-code files by type. Dispatch subagents IN PARALLEL — one per group:

```
You are a knowledge graph extraction agent. Read the files listed and extract entities and relationships.

Files: <FILE_LIST>

Extraction guidance by file type:
- **Markdown/text**: product features, architecture, decisions, defined terms, workflows. Skip generic headings.
- **DOCX**: people, places, concepts, events, organizations. Preserve original language.
- **Scanned PDF**: use vision to read pages. Extract authors, titles, topics, people, citations.
- **Images (HEIC/PNG/JPG)**: use vision. Describe content, OCR text, identify people/places. Group consecutive pages.

Rules:
- EXTRACTED = explicit in source (link, citation, direct reference)
- INFERRED = reasonable inference (shared concept, implied dependency)

Write valid JSON to: <OUTPUT_PATH>/wiki-out/semantic.json
{"nodes":[{"id":"unique_id","label":"Name","file_type":"document|paper|image","source_file":"path","source_location":""}],"edges":[{"source":"id","target":"id","relation":"references|defines|discusses|mentions|authored_by|part_of|related_to","confidence":"EXTRACTED|INFERRED","source_file":"path"}]}
```

### Step 3 — Merge and rebuild

```bash
python3 -c "
import json; from pathlib import Path
from my_llm_wiki import build, cluster, score_all, label_communities, detect
from my_llm_wiki import god_nodes, surprising_connections, suggest_questions
from my_llm_wiki import generate, to_json, to_html, to_wiki, to_vault

info = detect(Path('.'))
existing = json.loads(Path('wiki-out/graph.json').read_text())
semantic = json.loads(Path('wiki-out/semantic.json').read_text())
G = build([{'nodes': existing.get('nodes',[]), 'edges': existing.get('links',[])}, semantic])
communities = cluster(G)
cohesion = score_all(G, communities)
labels = label_communities(G, communities)
out = Path('wiki-out')
to_json(G, communities, str(out/'graph.json'))
to_html(G, communities, str(out/'graph.html'), labels)
to_wiki(G, communities, str(out/'wiki'), labels, cohesion, god_nodes(G))
to_vault(G, communities, str(out/'vault'), labels, cohesion)
report = generate(G, communities, cohesion, labels, god_nodes(G),
    surprising_connections(G, communities), info,
    token_cost={'input':0,'output':0}, root='.',
    suggested_questions=suggest_questions(G, communities, labels))
(out/'WIKI_REPORT.md').write_text(report, encoding='utf-8')
print(f'Enhanced: {G.number_of_nodes()} nodes · {G.number_of_edges()} edges · {len(communities)} communities')
"
```

### Step 4 — Health check

```bash
llm-wiki lint
```

Reports orphan nodes, tiny communities, confidence breakdown. Fix issues before proceeding.

### Step 5 — Report

Print node/edge/community counts. Offer to answer questions using `llm-wiki query`.

---

## Living Wiki Mode

Karpathy's vision: wiki is a **persistent, compounding artifact** — it grows with every session.

After initial build, follow this cycle:

```
Monitor → Rebuild → Lint → Write-back → Report
   ↑                                       │
   └───────────────────────────────────────┘
```

### Monitor — detect changes

```bash
# Check what changed since last build
LAST=$(stat -f %m wiki-out/graph.json 2>/dev/null || echo 0)
CHANGED=$(find . -name "*.py" -o -name "*.java" -o -name "*.md" -newer wiki-out/graph.json | wc -l)
echo "$CHANGED files changed since last build"
```

Or use continuous watch: `llm-wiki watch .`

### Rebuild — update graph

```bash
llm-wiki .   # SHA256 cache skips unchanged files
```

### Lint — check health

```bash
llm-wiki lint
```

If orphans or high ambiguity found, investigate and fix.

### Write-back — file insights into the graph

After answering a question or discovering something, write it back:

```bash
# Save insight as markdown for next rebuild
mkdir -p wiki-out/ingested
cat > wiki-out/ingested/insight_$(date +%Y%m%d).md << 'EOF'
---
type: insight
date: 2026-04-08
---
# GraphStore connects to MemoryStore via shared SQLite connection
Discovered during debugging session. The connection pool is shared,
which means GraphStore operations can block MemoryStore queries.
EOF

# Rebuild to include the insight
llm-wiki .
```

### Report — track growth

```bash
llm-wiki query stats   # current size
llm-wiki lint          # health
```

---

## CLI Reference

```bash
llm-wiki .                          # build graph
llm-wiki /path/to/folder            # build from specific path
llm-wiki --no-viz .                 # skip HTML viz (large graphs)
llm-wiki query search <terms>       # keyword search
llm-wiki query node <label>         # node details
llm-wiki query neighbors <label>    # direct connections
llm-wiki query community <id>       # list community members
llm-wiki query path <A> <B>         # shortest path
llm-wiki query gods                 # most connected nodes
llm-wiki query stats                # summary statistics
llm-wiki lint                       # graph health check
llm-wiki watch .                    # auto-rebuild on changes
llm-wiki add <url>                  # fetch URL as markdown
llm-wiki --version                  # show version
llm-wiki --help                     # show help
```

---

## When Is Agent Mode Worth It?

| File Type | Structural | + Agent | Verdict |
|-----------|-----------|---------|---------|
| Code (18 langs) | Full AST + doc comments | — | Skip agent |
| Markdown | Headings + links | 2x entities | Optional |
| DOCX | Hub nodes only | 30x entities | **Use agent** |
| Scanned PDF | 0 text | 85x entities | **Use agent** |
| Images | Hub nodes only | Vision OCR | **Use agent** |

---

## Installation

```bash
pip install my-llm-wiki
pip install my-llm-wiki[all]   # PDF + .docx/.xlsx + Leiden
```
