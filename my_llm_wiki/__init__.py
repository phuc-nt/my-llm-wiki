"""my-llm-wiki — turn any folder into a queryable knowledge graph.

Pipeline: detect → extract → build → cluster → analyze → report → export

Usage:
    from my_llm_wiki import detect, extract, build, cluster, analyze, generate, to_html, to_vault
"""
from __future__ import annotations
import importlib


def __getattr__(name: str):
    """Lazy imports — all heavy deps load only when accessed."""
    _map = {
        # detection
        "detect": ("my_llm_wiki.detect-files", "detect"),
        "classify_file": ("my_llm_wiki.detect-files", "classify_file"),
        "detect_incremental": ("my_llm_wiki.detect-office-convert", "detect_incremental"),
        # extraction
        "extract": ("my_llm_wiki.extract-public-api", "extract"),
        "collect_files": ("my_llm_wiki.extract-public-api", "collect_files"),
        # graph build
        "build_from_json": ("my_llm_wiki.build-graph", "build_from_json"),
        "build": ("my_llm_wiki.build-graph", "build"),
        # clustering
        "cluster": ("my_llm_wiki.cluster-communities", "cluster"),
        "score_all": ("my_llm_wiki.cluster-communities", "score_all"),
        "cohesion_score": ("my_llm_wiki.cluster-communities", "cohesion_score"),
        "label_communities": ("my_llm_wiki.cluster-label-communities", "label_communities"),
        # analysis
        "god_nodes": ("my_llm_wiki.analyze-graph", "god_nodes"),
        "surprising_connections": ("my_llm_wiki.analyze-graph", "surprising_connections"),
        "suggest_questions": ("my_llm_wiki.analyze-questions", "suggest_questions"),
        # report
        "generate": ("my_llm_wiki.report-markdown", "generate"),
        # exports
        "to_json": ("my_llm_wiki.export-json", "to_json"),
        "to_html": ("my_llm_wiki.export-html", "to_html"),
        "to_wiki": ("my_llm_wiki.export-wiki", "to_wiki"),
        "to_vault": ("my_llm_wiki.export-vault", "to_vault"),
        # doc extraction
        "extract_docs": ("my_llm_wiki.extract-docs", "extract_docs"),
        # query
        "query_main": ("my_llm_wiki.query-graph", "query_main"),
    }
    if name in _map:
        mod_name, attr = _map[name]
        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(f"module 'my_llm_wiki' has no attribute {name!r}")
