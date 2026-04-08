<p align="center">
  <img src="assets/logo.svg" width="120" alt="my-llm-wiki logo" />
</p>

<h1 align="center">my-llm-wiki</h1>

<p align="center">
  Turn any folder of code, docs, papers, or images into a queryable knowledge graph.
</p>

<p align="center">
  <a href="https://phuc-nt.github.io/my-llm-wiki/">Documentation</a> ·
  <a href="https://pypi.org/project/my-llm-wiki/">PyPI</a> ·
  <a href="https://github.com/phuc-nt/my-llm-wiki/issues">Issues</a>
</p>

---

Inspired by [Andrej Karpathy's LLM Wiki concept](https://x.com/karpathy/status/1909380524543902036): drop raw files → compile once → query forever.

## Install

```bash
pip install my-llm-wiki
pip install my-llm-wiki[all]   # PDF + .docx/.xlsx + Leiden clustering
```

## Usage

```bash
llm-wiki .                          # build graph → wiki-out/
llm-wiki query gods                 # most connected nodes
llm-wiki query search <term>        # keyword search
llm-wiki query neighbors <label>    # direct connections
llm-wiki query path <A> <B>         # shortest path
llm-wiki watch .                    # auto-rebuild on changes
llm-wiki add <url>                  # ingest URL as markdown
```

## Claude Code Skill

For deep extraction of DOCX, scanned PDFs, and images via agent mode:

```bash
mkdir -p ~/.claude/skills/my-llm-wiki
cp "$(python -c 'import my_llm_wiki; print(my_llm_wiki.__path__[0])')/SKILL.md" ~/.claude/skills/my-llm-wiki/
```

Then `/wiki .` in Claude Code runs structural + semantic extraction.

## Docs

Full documentation at **[phuc-nt.github.io/my-llm-wiki](https://phuc-nt.github.io/my-llm-wiki/)**

## License

[MIT](LICENSE)
