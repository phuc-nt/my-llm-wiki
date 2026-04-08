---
layout: default
title: Use Cases
nav_order: 5
description: "Real-world scenarios for my-llm-wiki: codebases, research, personal knowledge."
---

# Use Cases

## Understand a new codebase

You join a team. The repo has 200 files across 15 modules. Instead of reading code file by file:

```bash
cd the-repo && llm-wiki .
llm-wiki query gods              # what are the core abstractions?
llm-wiki query community 0       # what's in the biggest cluster?
llm-wiki query path Auth Database # how does auth reach the DB?
```

Open `graph.html` to visually explore — click nodes, filter by community, trace paths.

---

## Build a research corpus

Drop papers, notes, tweets, blog posts into a folder. Build once, query across all of them:

```bash
llm-wiki add https://arxiv.org/abs/2401.12345 --author "Smith et al."
llm-wiki add https://karpathy.ai/blog/llm-wiki
llm-wiki .
llm-wiki query search "attention mechanism"
llm-wiki query path "transformer" "diffusion"
```

The graph shows connections between papers you didn't know were related.

---

## Personal /raw folder (Karpathy workflow)

The original concept: one folder where you drop everything.

```
~/raw/
  papers/attention-is-all-you-need.pdf
  notes/meeting-2026-04.md
  screenshots/architecture-whiteboard.png
  code/prototype/main.py
```

```bash
cd ~/raw && llm-wiki .
```

Code gets AST extraction. Docs get structural parsing. Use `/wiki .` in Claude Code for deep extraction of PDFs and images.

---

## Vietnamese historical documents

Tested with Thượng Chi Văn Tập (Phạm Quỳnh) and Nam Phong Tạp Chí:

- **DOCX** (43K chars Vietnamese text): 3 hub nodes → 103 entities after agent extraction
- **Scanned PDF** (1007 pages): 0 text via pypdf → 86 entities after agent vision
- **HEIC scans** (13 images): 0 text → 29 entities with character names, places, themes

Agent mode preserves Vietnamese labels and extracts culturally specific entities.

---

## Documentation audit

Run on your docs folder to find:

- **God nodes** — most referenced concepts (are they well-documented?)
- **Orphan nodes** — concepts with no connections (missing cross-references?)
- **Surprising connections** — unexpected links between docs
- **Community structure** — do your docs cluster the way you expect?

```bash
llm-wiki query gods    # what's most referenced?
llm-wiki query stats   # how much is INFERRED vs EXTRACTED?
```

---

## Claude Code integration

After building the graph, Claude can answer questions without re-reading source files:

```bash
# Install the skill
mkdir -p ~/.claude/skills/my-llm-wiki
cp "$(python -c 'import my_llm_wiki; print(my_llm_wiki.__path__[0])')/SKILL.md" ~/.claude/skills/my-llm-wiki/

# Then in Claude Code:
# /wiki .           → full pipeline with agent enhancement
# "what connects GraphStore to Settings?" → Claude uses llm-wiki query
```
