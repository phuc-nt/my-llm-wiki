# my-llm-wiki

Turn any folder of code, docs, papers, or images into a queryable knowledge graph.

**Karpathy LLM Wiki concept**: drop raw files → compile once → query forever.

---

## What You Must Do When `/wiki` is Invoked

If no path given, use `.` (current directory). Follow these steps in order.

### Step 1 — Structural extraction

```bash
llm-wiki .
```

This runs: detect → AST (code) → structural (docs) → cross-reference → build → cluster → export.
Output goes to `wiki-out/`. Read the summary output — note what file types were found.

**What structural extraction handles well:**
- Code files (18 languages) → AST nodes, edges, cross-file imports
- Markdown/text → headings, definitions, cross-doc links
- Code↔doc cross-references → automatic `mentions` edges

**What needs agent-mode enhancement (Step 2):**
- DOCX without markdown headings → structural creates hub nodes only
- Scanned PDFs → pypdf returns 0 text, only hub node created
- Images (PNG, JPG, HEIC) → hub nodes only, no content extraction
- Rich domain knowledge in any doc that structural parsing misses

### Step 2 — Semantic extraction (agent mode)

Check Step 1 output. If it reports docs/papers/images with few edges, enhance with agents.

**Step 2a — Identify files by type:**

Read the Step 1 output and `.graphify_detect.json` or re-run detect to categorize files:
- **Text/Markdown** with good structural results (many nodes) → skip, already extracted
- **DOCX** with 0 edges → needs agent
- **PDF** with 0 words → scanned, needs agent with vision
- **Images** → needs agent with vision

**Step 2b — Dispatch extraction agents by file type:**

Group files by type. Dispatch subagents IN PARALLEL — one per group. Use these tested prompts:

**For Markdown/Text docs** (only if structural extraction was thin):
```
You are a knowledge graph extraction agent. Read the files listed and extract domain-specific entities and relationships.
Focus on: product features, architecture, key decisions, defined terms, workflows.
Skip generic terms (Next Steps, Overview, Troubleshooting, etc.)
Rules: EXTRACTED = explicit in source. INFERRED = reasonable inference.
Files: <FILE_LIST>
Write JSON to: <OUTPUT_PATH>/wiki-out/semantic.json
Format: {"nodes":[{"id":"unique_id","label":"Name","file_type":"document","source_file":"path","source_location":""}],"edges":[{"source":"id","target":"id","relation":"references|defines|part_of|uses|depends_on|related_to","confidence":"EXTRACTED|INFERRED","source_file":"path"}]}
```

**For DOCX files** (structural creates hub nodes only — agent essential):
```
You are a knowledge graph extraction agent. Read these documents and extract entities and relationships.
Extract: people, places, concepts, events, organizations, and how they relate.
Labels should preserve the original language where appropriate.
Rules: EXTRACTED = explicit in source. INFERRED = reasonable inference.
Files: <FILE_LIST>
Write JSON to: <OUTPUT_PATH>/wiki-out/semantic.json
Format: {"nodes":[{"id":"unique_id","label":"Name","file_type":"document","source_file":"path","source_location":""}],"edges":[{"source":"id","target":"id","relation":"discusses|mentions|authored_by|located_in|part_of|related_to|compares","confidence":"EXTRACTED|INFERRED","source_file":"path"}]}
```

**For scanned PDFs** (pypdf returns 0 text — agent reads pages with vision):
```
You are a knowledge graph extraction agent. Read this scanned PDF using vision.
The PDF is scanned — use the Read tool to view pages visually.
Extract: authors, titles, topics, people, places, concepts, citations.
Rules: EXTRACTED = visible in source. INFERRED = reasonable inference.
File: <FILE_PATH>
Write JSON to: <OUTPUT_PATH>/wiki-out/semantic.json
Format: {"nodes":[{"id":"unique_id","label":"Name","file_type":"paper","source_file":"path","source_location":""}],"edges":[{"source":"id","target":"id","relation":"published_in|authored_by|discusses|mentions|cites|related_to","confidence":"EXTRACTED|INFERRED","source_file":"path"}]}
```

**For images** (HEIC, PNG, JPG — agent uses vision):
```
You are a knowledge graph extraction agent with vision. Read these images using the Read tool.
For each image: describe what you see, extract text (OCR), identify people/places/concepts.
Group related images (e.g., consecutive pages of same document) into one entity.
Rules: EXTRACTED = visible in image. INFERRED = contextual inference.
Files: <FILE_LIST>
Write JSON to: <OUTPUT_PATH>/wiki-out/semantic.json
Format: {"nodes":[{"id":"unique_id","label":"Name","file_type":"image","source_file":"path","source_location":""}],"edges":[{"source":"id","target":"id","relation":"depicts|mentions|authored_by|related_to|part_of","confidence":"EXTRACTED|INFERRED","source_file":"path"}]}
```

**Step 2c — Merge semantic results into graph:**

Collect JSON from all subagents. If multiple agents wrote separate files, merge them first. Then rebuild:

```bash
python3 -c "
import json
from pathlib import Path
from my_llm_wiki import build, cluster, score_all, label_communities, detect
from my_llm_wiki import god_nodes, surprising_connections, suggest_questions
from my_llm_wiki import generate, to_json, to_html, to_wiki, to_vault

info = detect(Path('.'))
existing = json.loads(Path('wiki-out/graph.json').read_text())
semantic = json.loads(Path('wiki-out/semantic.json').read_text())

G = build([
    {'nodes': existing.get('nodes', []), 'edges': existing.get('links', [])},
    semantic,
])
communities = cluster(G)
cohesion = score_all(G, communities)
labels = label_communities(G, communities)
out = Path('wiki-out')
to_json(G, communities, str(out/'graph.json'))
to_html(G, communities, str(out/'graph.html'), labels)
to_wiki(G, communities, str(out/'wiki'), labels, cohesion, god_nodes(G))
to_vault(G, communities, str(out/'vault'), labels, cohesion)
report = generate(G, communities, cohesion, labels,
    god_nodes(G), surprising_connections(G, communities), info,
    token_cost={'input':0,'output':0}, root='.',
    suggested_questions=suggest_questions(G, communities, labels))
(out/'WIKI_REPORT.md').write_text(report, encoding='utf-8')
print(f'Enhanced: {G.number_of_nodes()} nodes · {G.number_of_edges()} edges · {len(communities)} communities')
"
```

### Step 3 — Report results

```
Wiki built: X nodes · Y edges · Z communities
  graph.html  — interactive visualization
  WIKI_REPORT.md — analysis report
  vault/      — markdown vault with [[wikilinks]]

Ask me anything, or run: llm-wiki query search <term>
```

---

## CLI Reference

```bash
llm-wiki .                          # build graph
llm-wiki /path/to/folder            # build from specific path
llm-wiki query search <terms>       # keyword search
llm-wiki query node <label>         # node details
llm-wiki query neighbors <label>    # direct connections
llm-wiki query community <id>       # list community members
llm-wiki query path <A> <B>         # shortest path
llm-wiki query gods                 # most connected nodes
llm-wiki query stats                # summary statistics
llm-wiki watch .                    # auto-rebuild on changes
llm-wiki add <url>                  # fetch URL, save as markdown
```

---

## Tested Extraction Quality by File Type

| File Type | Structural (free) | + Agent (semantic) | Agent Needed? |
|-----------|-------------------|-------------------|---------------|
| Code (.py, .ts, etc.) | Full AST extraction | N/A | No |
| Markdown (.md, .txt) | Headings + definitions + links | 2x more entities | Optional |
| DOCX | Hub nodes only | 30x more entities | **Yes** |
| Scanned PDF | Hub node, 0 text | 85x more entities | **Yes** |
| Images (HEIC, PNG, JPG) | Hub nodes only | Vision extracts content | **Yes** |
| Text PDF | Text + headings | Deeper concepts | Optional |

---

## Installation

```bash
pip install my-llm-wiki
pip install my-llm-wiki[all]   # PDF + .docx/.xlsx + Leiden clustering
```
