"""Generate knowledge-gap questions from the graph: ambiguous edges, bridge nodes, isolated nodes, low cohesion."""
from __future__ import annotations
import importlib
import networkx as nx

# Import helpers from analyze-graph and cluster-communities (kebab-case modules via importlib)
_ag = importlib.import_module("my_llm_wiki.analyze-graph")
_node_community_map = _ag._node_community_map
_is_file_node = _ag._is_file_node
_is_concept_node = _ag._is_concept_node
_surprise_score = _ag._surprise_score  # defined in analyze-graph to avoid circular import

_cc = importlib.import_module("my_llm_wiki.cluster-communities")
cohesion_score = _cc.cohesion_score


def suggest_questions(
    G: nx.Graph,
    communities: dict[int, list[str]],
    community_labels: dict[int, str],
    top_n: int = 7,
) -> list[dict]:
    """Generate questions the graph is uniquely positioned to answer.

    Based on: AMBIGUOUS edges, bridge nodes, underexplored god nodes, isolated nodes,
    and low-cohesion communities. Each question has a 'type', 'question', and 'why'.
    """
    questions: list[dict] = []
    node_community = _node_community_map(communities)

    # 1. AMBIGUOUS edges → unresolved relationship questions
    for u, v, data in G.edges(data=True):
        if data.get("confidence") == "AMBIGUOUS":
            ul = G.nodes[u].get("label", u)
            vl = G.nodes[v].get("label", v)
            relation = data.get("relation", "related to")
            questions.append({
                "type": "ambiguous_edge",
                "question": f"What is the exact relationship between `{ul}` and `{vl}`?",
                "why": f"Edge tagged AMBIGUOUS (relation: {relation}) - confidence is low.",
            })

    # 2. Bridge nodes (high betweenness) → cross-cutting concern questions
    if G.number_of_edges() > 0:
        betweenness = nx.betweenness_centrality(G)
        bridges = sorted(
            [(n, s) for n, s in betweenness.items()
             if not _is_file_node(G, n) and not _is_concept_node(G, n) and s > 0],
            key=lambda x: x[1],
            reverse=True,
        )[:3]
        for node_id, score in bridges:
            label = G.nodes[node_id].get("label", node_id)
            cid = node_community.get(node_id)
            comm_label = community_labels.get(cid, f"Community {cid}") if cid is not None else "unknown"
            neighbors = list(G.neighbors(node_id))
            neighbor_comms = {node_community.get(n) for n in neighbors if node_community.get(n) != cid}
            if neighbor_comms:
                other_labels = [community_labels.get(c, f"Community {c}") for c in neighbor_comms]
                questions.append({
                    "type": "bridge_node",
                    "question": f"Why does `{label}` connect `{comm_label}` to {', '.join(f'`{l}`' for l in other_labels)}?",
                    "why": f"High betweenness centrality ({score:.3f}) - this node is a cross-community bridge.",
                })

    # 3. God nodes with many INFERRED edges → verification questions
    degree = dict(G.degree())
    top_nodes = sorted(
        [(n, d) for n, d in degree.items() if not _is_file_node(G, n)],
        key=lambda x: x[1],
        reverse=True,
    )[:5]
    for node_id, _ in top_nodes:
        inferred = [
            (u, v, d) for u, v, d in G.edges(node_id, data=True)
            if d.get("confidence") == "INFERRED"
        ]
        if len(inferred) >= 2:
            label = G.nodes[node_id].get("label", node_id)
            others = []
            for u, v, d in inferred[:2]:
                src_id = d.get("_src", u)
                tgt_id = d.get("_tgt", v)
                other_id = tgt_id if src_id == node_id else src_id
                others.append(G.nodes[other_id].get("label", other_id))
            questions.append({
                "type": "verify_inferred",
                "question": f"Are the {len(inferred)} inferred relationships involving `{label}` (e.g. with `{others[0]}` and `{others[1]}`) actually correct?",
                "why": f"`{label}` has {len(inferred)} INFERRED edges - model-reasoned connections that need verification.",
            })

    # 4. Isolated or weakly-connected nodes → exploration questions
    isolated = [
        n for n in G.nodes()
        if G.degree(n) <= 1 and not _is_file_node(G, n) and not _is_concept_node(G, n)
    ]
    if isolated:
        labels = [G.nodes[n].get("label", n) for n in isolated[:3]]
        questions.append({
            "type": "isolated_nodes",
            "question": f"What connects {', '.join(f'`{l}`' for l in labels)} to the rest of the system?",
            "why": f"{len(isolated)} weakly-connected nodes found - possible documentation gaps or missing edges.",
        })

    # 5. Low-cohesion communities → structural questions
    for cid, nodes in communities.items():
        score = cohesion_score(G, nodes)
        if score < 0.15 and len(nodes) >= 5:
            label = community_labels.get(cid, f"Community {cid}")
            questions.append({
                "type": "low_cohesion",
                "question": f"Should `{label}` be split into smaller, more focused modules?",
                "why": f"Cohesion score {score} - nodes in this community are weakly interconnected.",
            })

    if not questions:
        return [{
            "type": "no_signal",
            "question": None,
            "why": (
                "Not enough signal to generate questions. "
                "This usually means the corpus has no AMBIGUOUS edges, no bridge nodes, "
                "no INFERRED relationships, and all communities are tightly cohesive. "
                "Add more files or run with --mode deep to extract richer edges."
            ),
        }]

    return questions[:top_n]
