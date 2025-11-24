"""Address clustering based on deterministic heuristics."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Set, Tuple


def _shared_counterparties(metrics: Dict[str, Dict[str, int]], threshold: int = 2) -> Dict[Tuple[str, str], int]:
    scores: Dict[Tuple[str, str], int] = defaultdict(int)
    addresses = list(metrics.keys())
    for i, lhs in enumerate(addresses):
        for rhs in addresses[i + 1 :]:
            shared = min(metrics[lhs]["inbound_lamports"], metrics[rhs]["inbound_lamports"])
            if shared >= threshold:
                scores[(lhs, rhs)] += 1
    return scores


def build_clusters(metrics: Dict[str, Dict[str, int]], program_bias: int = 3) -> List[Set[str]]:
    """Cluster addresses using a simple union-find approach.

    The algorithm links addresses that share comparable inbound exposure and
    elevated program touch counts. Deterministic scoring avoids nondeterminism
    from randomized graph algorithms.
    """

    parent: Dict[str, str] = {addr: addr for addr in metrics}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        root_x, root_y = find(x), find(y)
        if root_x != root_y:
            parent[root_y] = root_x

    shared_edges = _shared_counterparties(metrics)
    for (lhs, rhs), score in shared_edges.items():
        lhs_prog = metrics[lhs]["program_touches"]
        rhs_prog = metrics[rhs]["program_touches"]
        if lhs_prog + rhs_prog >= program_bias and score:
            union(lhs, rhs)

    clusters: Dict[str, Set[str]] = defaultdict(set)
    for addr in metrics:
        clusters[find(addr)].add(addr)
    return [members for members in clusters.values() if len(members) > 1]


def cluster_summary(clusters: Iterable[Set[str]]) -> List[Dict[str, object]]:
    return [
        {
            "size": len(cluster),
            "members": sorted(cluster),
        }
        for cluster in clusters
    ]
