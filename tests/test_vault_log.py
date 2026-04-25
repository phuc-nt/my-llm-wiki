"""Tests for vault/log.md append-only chronological record (A2)."""
from __future__ import annotations

import re
from pathlib import Path

import networkx as nx

from my_llm_wiki import append_log_entry, to_vault, write_note


def _build_minimal_graph() -> tuple[nx.Graph, dict[int, list[str]]]:
    G = nx.Graph()
    G.add_node("a", label="A", file_type="code")
    G.add_node("b", label="B", file_type="code")
    G.add_edge("a", "b", relation="calls")
    return G, {0: ["a", "b"]}


def test_append_creates_log_when_missing(tmp_path: Path) -> None:
    append_log_entry(tmp_path, "build", "421 nodes")
    log = tmp_path / "log.md"
    assert log.exists()
    text = log.read_text(encoding="utf-8")
    assert text.startswith("# Vault Activity Log")
    assert "build" in text
    assert "421 nodes" in text


def test_append_preserves_existing_entries(tmp_path: Path) -> None:
    append_log_entry(tmp_path, "build", "first")
    append_log_entry(tmp_path, "note", "second")
    text = (tmp_path / "log.md").read_text(encoding="utf-8")
    # Both entries present, chronological order preserved
    first_idx = text.index("first")
    second_idx = text.index("second")
    assert first_idx < second_idx
    assert "build" in text and "note" in text


def test_log_entry_format_has_iso_timestamp(tmp_path: Path) -> None:
    append_log_entry(tmp_path, "build", "test")
    text = (tmp_path / "log.md").read_text(encoding="utf-8")
    # Format: ## [YYYY-MM-DD HH:MM] [op] | desc
    pattern = r"## \[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] \[build\] \| test"
    assert re.search(pattern, text), f"timestamp/format mismatch in: {text}"


def test_to_vault_writes_build_entry(tmp_path: Path) -> None:
    G, comms = _build_minimal_graph()
    to_vault(G, comms, str(tmp_path), community_labels={0: "Code"})
    log = tmp_path / "log.md"
    assert log.exists()
    text = log.read_text(encoding="utf-8")
    assert "[build]" in text
    assert "2 nodes" in text
    assert "1 edges" in text or "1 edge" in text
    assert "1 communities" in text or "1 community" in text


def test_write_note_appends_log_entry_when_vault_present(tmp_path: Path) -> None:
    # Simulate the wiki-out layout: vault/ + ingested/ siblings
    wiki_out = tmp_path / "wiki-out"
    vault_dir = wiki_out / "vault"
    ingested_dir = wiki_out / "ingested"
    vault_dir.mkdir(parents=True)

    write_note("Cache uses SHA256 because reproducibility matters",
               output_dir=str(ingested_dir),
               links=["GraphStore"], tags=["rationale"])

    log = vault_dir / "log.md"
    assert log.exists()
    text = log.read_text(encoding="utf-8")
    assert "[note]" in text
    assert "GraphStore" in text or "Cache uses SHA256" in text


def test_write_note_skips_log_when_vault_absent(tmp_path: Path) -> None:
    # No vault/ sibling — note still works, just no log entry created
    ingested_dir = tmp_path / "ingested"
    write_note("test note text", output_dir=str(ingested_dir))
    # Note file written
    assert any(ingested_dir.glob("note-*.md"))
    # No log.md created anywhere under tmp_path
    assert not list(tmp_path.rglob("log.md"))
