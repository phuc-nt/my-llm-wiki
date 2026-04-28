"""TDD tests for D5: per-heading page citations on document nodes.

Verifies that heading nodes extracted from PDFs carry a `page` integer
attribute reflecting which page the heading appears on. Each heading on a
distinct page must have the correct 1-indexed page number.

Spike finding (2026-04-28): Docling 2.91 emits page_no per heading via
provenance — 1-indexed, one entry per heading item. The _normalize helper in
extract-with-docling.py already captures this. The gap was in extract-docs.py
which only received plain text (no page info) from _read_file_text.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

_extract_docs = importlib.import_module("my_llm_wiki.extract-docs")
_docling = importlib.import_module("my_llm_wiki.extract-with-docling")


def _make_pdf_with_headings(path: Path) -> None:
    """Generate a 3-page PDF with one distinct heading per page via reportlab."""
    try:
        from reportlab.pdfgen import canvas
    except ImportError:
        pytest.skip("reportlab not installed")

    c = canvas.Canvas(str(path))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 720, "Heading Alpha")
    c.setFont("Helvetica", 12)
    c.drawString(72, 680, "Body text on page one.")
    c.showPage()

    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 720, "Heading Beta")
    c.setFont("Helvetica", 12)
    c.drawString(72, 680, "Body text on page two.")
    c.showPage()

    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 720, "Heading Gamma")
    c.setFont("Helvetica", 12)
    c.drawString(72, 680, "Body text on page three.")
    c.showPage()
    c.save()


@pytest.mark.skipif(
    not _docling.is_docling_available(),
    reason="docling not installed",
)
def test_heading_nodes_carry_page_attribute(tmp_path: Path) -> None:
    """Each heading node from a multi-page PDF must carry the correct page int."""
    pdf = tmp_path / "headings.pdf"
    _make_pdf_with_headings(pdf)

    result = _extract_docs.extract_doc(pdf)
    nodes = result["nodes"]
    assert nodes, "expected at least the hub node"

    # Collect heading nodes (non-hub, file_type paper/document, have source_location != 'L1')
    # Hub node has source_location 'L1' and label == pdf.stem
    hub_label = pdf.stem
    heading_nodes = [
        n for n in nodes
        if n.get("label") != hub_label
    ]

    # Should have 3 heading nodes (Alpha, Beta, Gamma)
    heading_labels = {n["label"] for n in heading_nodes}
    assert "Heading Alpha" in heading_labels, f"Missing 'Heading Alpha' in {heading_labels}"
    assert "Heading Beta" in heading_labels, f"Missing 'Heading Beta' in {heading_labels}"
    assert "Heading Gamma" in heading_labels, f"Missing 'Heading Gamma' in {heading_labels}"

    # Each heading node must carry the `page` attribute
    label_to_page = {n["label"]: n.get("page") for n in heading_nodes}
    assert label_to_page.get("Heading Alpha") == 1, (
        f"Expected page=1 for 'Heading Alpha', got {label_to_page.get('Heading Alpha')}"
    )
    assert label_to_page.get("Heading Beta") == 2, (
        f"Expected page=2 for 'Heading Beta', got {label_to_page.get('Heading Beta')}"
    )
    assert label_to_page.get("Heading Gamma") == 3, (
        f"Expected page=3 for 'Heading Gamma', got {label_to_page.get('Heading Gamma')}"
    )


@pytest.mark.skipif(
    not _docling.is_docling_available(),
    reason="docling not installed",
)
def test_heading_page_is_integer(tmp_path: Path) -> None:
    """Page attribute must be a Python int (not string, None, or float)."""
    pdf = tmp_path / "headings2.pdf"
    _make_pdf_with_headings(pdf)

    result = _extract_docs.extract_doc(pdf)
    hub_label = pdf.stem
    heading_nodes = [n for n in result["nodes"] if n.get("label") != hub_label and "page" in n]
    assert heading_nodes, "expected heading nodes with page attr"
    for node in heading_nodes:
        assert isinstance(node["page"], int), (
            f"page attr must be int, got {type(node['page'])} for {node['label']!r}"
        )


def test_markdown_heading_nodes_have_no_page_attr(tmp_path: Path) -> None:
    """Markdown heading nodes must NOT carry a `page` attribute (no page concept)."""
    md = tmp_path / "doc.md"
    md.write_text("# Introduction\n\nBody.\n\n## Details\n\nMore.\n", encoding="utf-8")
    result = _extract_docs.extract_doc(md)
    hub_label = md.stem
    heading_nodes = [n for n in result["nodes"] if n.get("label") != hub_label]
    for node in heading_nodes:
        assert "page" not in node, (
            f"Markdown node {node['label']!r} must not have 'page' attr"
        )


def test_export_vault_includes_page_in_frontmatter(tmp_path: Path) -> None:
    """Vault note for a node with `page` attr must include `page: N` in YAML frontmatter."""
    import networkx as nx
    _export_vault = importlib.import_module("my_llm_wiki.export-vault")

    G = nx.Graph()
    G.add_node("node1", label="Section One", file_type="paper", source_file="doc.pdf",
               source_location="L1", page=5)
    G.add_node("node2", label="doc", file_type="paper", source_file="doc.pdf",
               source_location="L1", pages=10)
    G.add_edge("node2", "node1", relation="contains", confidence="EXTRACTED", source_file="doc.pdf")

    communities = {0: ["node1", "node2"]}
    out = tmp_path / "vault"
    _export_vault.to_vault(G, communities, str(out))

    # Find the note for "Section One"
    note_path = out / "paper" / "Section One.md"
    assert note_path.exists(), f"Expected {note_path} to exist"
    content = note_path.read_text(encoding="utf-8")
    assert "page: 5" in content, f"Expected 'page: 5' in frontmatter, got:\n{content}"


def test_cmd_node_shows_page(tmp_path: Path) -> None:
    """query-graph cmd_node must print `Page: N` line when node has `page` attr."""
    import networkx as nx
    _query = importlib.import_module("my_llm_wiki.query-graph")

    G = nx.Graph()
    G.add_node("abc123", label="Introduction", file_type="paper",
               source_file="doc.pdf", source_location="L1", page=3)

    result = _query.cmd_node(G, "Introduction")
    assert "Page: 3" in result, f"Expected 'Page: 3' in cmd_node output, got:\n{result}"


def test_cmd_node_no_page_when_absent(tmp_path: Path) -> None:
    """cmd_node must NOT print Page line when node has no `page` attr."""
    import networkx as nx
    _query = importlib.import_module("my_llm_wiki.query-graph")

    G = nx.Graph()
    G.add_node("abc456", label="README", file_type="document",
               source_file="readme.md", source_location="L1")

    result = _query.cmd_node(G, "README")
    assert "Page:" not in result, f"Unexpected 'Page:' in cmd_node output:\n{result}"
