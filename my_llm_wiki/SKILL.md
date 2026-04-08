# my-llm-wiki

Turn any folder of code, docs, papers, or images into a queryable knowledge graph.

Drop raw files → compile once → query forever. Inspired by Karpathy's LLM Wiki concept.

---

## When `/wiki` is Invoked

If no path given, use `.` (current directory).

### Step 1 — Structural extraction (free, fast)

```bash
llm-wiki .
```

Read the summary output. Note file counts and edge counts per type.

**Code** gets full AST extraction — no agent needed.
**Markdown/text** gets headings, definitions, cross-doc links — usually sufficient.
**DOCX, scanned PDFs, images** get hub nodes only — proceed to Step 2.

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

### Step 4 — Report

Print node/edge/community counts. Offer to answer questions using `llm-wiki query`.

---

## Querying

```bash
llm-wiki query search <terms>       # keyword search
llm-wiki query node <label>         # node details
llm-wiki query neighbors <label>    # direct connections
llm-wiki query community <id>       # list community members
llm-wiki query path <A> <B>         # shortest path
llm-wiki query gods                 # most connected nodes
llm-wiki query stats                # summary statistics
```

For natural language questions: read `wiki-out/WIKI_REPORT.md` for overview, use `llm-wiki query` for specifics.

---

## Other Commands

```bash
llm-wiki watch .                    # auto-rebuild on file changes
llm-wiki add <url>                  # fetch URL, save as markdown
```

---

## When Is Agent Mode Worth It?

| File Type | Structural | + Agent | Verdict |
|-----------|-----------|---------|---------|
| Code | Full AST | — | Skip agent |
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
