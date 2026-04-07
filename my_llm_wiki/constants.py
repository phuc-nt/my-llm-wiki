# shared constants used across all modules
from __future__ import annotations

# output directory name — single source of truth
OUTPUT_DIR = "wiki-out"

# visualization limits
MAX_NODES_FOR_VIZ = 5_000

# community color palette (vis.js compatible, 10 colors)
COMMUNITY_COLORS = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
    "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac",
]

# confidence levels
CONFIDENCE_EXTRACTED = "EXTRACTED"
CONFIDENCE_INFERRED = "INFERRED"
CONFIDENCE_AMBIGUOUS = "AMBIGUOUS"
VALID_CONFIDENCES = {CONFIDENCE_EXTRACTED, CONFIDENCE_INFERRED, CONFIDENCE_AMBIGUOUS}

# file type classifications
VALID_FILE_TYPES = {"code", "document", "paper", "image"}
