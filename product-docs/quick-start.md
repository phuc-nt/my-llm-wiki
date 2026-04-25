---
layout: default
title: Install & Quick Start
nav_order: 6
description: "Install my-llm-wiki and build your first knowledge graph in 30 seconds."
---

# Install & Quick Start

## Install

```bash
pip install my-llm-wiki
```

Optional extras:

```bash
pip install my-llm-wiki[all]   # PDF + .docx/.xlsx + better clustering
```

## Build a graph

```bash
cd your-project
llm-wiki .
```

Output goes to `wiki-out/`:

```
wiki-out/
  graph.html       ← open in browser
  graph.json       ← persistent graph data
  WIKI_REPORT.md   ← analysis report
  wiki/            ← Wikipedia-style articles
  vault/           ← Obsidian vault — index.md catalog + [[wikilinks]] + YAML frontmatter
```

**Open in Obsidian:** Point Obsidian at `wiki-out/vault/` (Open folder as vault) — graph view, backlinks, tag pane, and Properties all work out of the box. Start from `index.md` (auto-generated catalog by file type + communities). Community colors are pre-configured via `.vault/graph.json`.

## Query

```bash
llm-wiki query gods                      # most connected nodes
llm-wiki query search "authentication"   # keyword search
llm-wiki query node UserService          # details + doc comment
llm-wiki query neighbors UserService     # what connects to it?
llm-wiki query path Auth Database        # shortest path
llm-wiki query community 0              # largest community
llm-wiki query stats                     # summary
```

## Health check

```bash
llm-wiki lint    # orphan nodes, tiny communities, confidence breakdown
```

## Keep the wiki alive

```bash
llm-wiki watch .                               # auto-rebuild on changes
llm-wiki add https://interesting-article.com   # ingest URL
llm-wiki .                                     # rebuild (cache skips unchanged)
```

## Claude Code skill (optional)

For deep extraction of DOCX, scanned PDFs, and images:

```bash
mkdir -p ~/.claude/skills/my-llm-wiki
cp "$(python -c 'import my_llm_wiki; print(my_llm_wiki.__path__[0])')/SKILL.md" ~/.claude/skills/my-llm-wiki/
```

Then in Claude Code, run `/wiki .` for the full pipeline with agent-mode semantic extraction.

## Ignore files

Create `.wikiignore` in project root (gitignore syntax):

```
vendor/
node_modules/
dist/
*.generated.py
```

## Supported languages

Python, JavaScript, TypeScript, Go, Rust, Java, C, C++, Ruby, C#, Kotlin, Scala, PHP, Swift, Lua, Zig, PowerShell, Elixir
