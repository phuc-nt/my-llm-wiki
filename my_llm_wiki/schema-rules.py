# user-defined schema rules from .wikischema file
# Validates and enriches nodes/edges based on user-specified entity types and rules
from __future__ import annotations
import json
from pathlib import Path

import networkx as nx

# Default schema when no .wikischema exists
_DEFAULT_SCHEMA = {
    "entity_types": ["code", "document", "paper", "image"],
    "relation_types": [
        "contains", "imports", "calls", "uses", "references",
        "defines", "explains", "related_to", "mentions",
        "same_concept", "rationale_for", "method",
    ],
    "required_fields": ["id", "label", "file_type", "source_file"],
}


def load_schema(root: Path) -> dict:
    """Load .wikischema from root, or return default schema."""
    schema_file = root / ".wikischema"
    if not schema_file.exists():
        return _DEFAULT_SCHEMA
    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        # Merge with defaults for missing fields
        for key, default in _DEFAULT_SCHEMA.items():
            if key not in schema:
                schema[key] = default
        return schema
    except (json.JSONDecodeError, OSError):
        return _DEFAULT_SCHEMA


def validate_graph(G: nx.Graph, schema: dict) -> list[str]:
    """Validate graph against schema rules. Returns list of warnings."""
    warnings: list[str] = []
    valid_types = set(schema.get("entity_types", []))
    valid_relations = set(schema.get("relation_types", []))

    for nid, data in G.nodes(data=True):
        ftype = data.get("file_type", "")
        if valid_types and ftype and ftype not in valid_types:
            warnings.append(f"Node '{data.get('label', nid)}': unknown type '{ftype}'")

    for u, v, data in G.edges(data=True):
        rel = data.get("relation", "")
        if valid_relations and rel and rel not in valid_relations:
            warnings.append(f"Edge '{rel}': unknown relation type")

    return warnings[:20]  # cap warnings
