from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set

from .heuristics import AddressStats


@dataclass
class AddressCluster:
    members: Set[str]
    score: float


class GraphClusterer:
    """Union-find clustering for addresses sharing transaction flows."""

    def __init__(self, similarity_threshold: float = 0.5):
        self.parent: Dict[str, str] = {}
        self.size: Dict[str, int] = {}
        self.threshold = similarity_threshold

    def find(self, addr: str) -> str:
        if addr not in self.parent:
            self.parent[addr] = addr
            self.size[addr] = 1
            return addr
        while addr != self.parent[addr]:
            self.parent[addr] = self.parent[self.parent[addr]]
            addr = self.parent[addr]
        return addr

    def union(self, a: str, b: str) -> None:
        root_a, root_b = self.find(a), self.find(b)
        if root_a == root_b:
            return
        if self.size[root_a] < self.size[root_b]:
            root_a, root_b = root_b, root_a
        self.parent[root_b] = root_a
        self.size[root_a] += self.size[root_b]

    def cluster_by_flow_similarity(self, stats: Iterable[AddressStats]) -> List[AddressCluster]:
        by_addr = {s.address: s for s in stats}
        addresses = list(by_addr.keys())
        for i, addr_a in enumerate(addresses):
            for addr_b in addresses[i + 1 :]:
                sim = self._similarity(by_addr[addr_a], by_addr[addr_b])
                if sim >= self.threshold:
                    self.union(addr_a, addr_b)

        buckets: Dict[str, Set[str]] = defaultdict(set)
        for addr in addresses:
            buckets[self.find(addr)].add(addr)

        clusters: List[AddressCluster] = []
        for members in buckets.values():
            score = sum(self._score(by_addr[m]) for m in members) / len(members)
            clusters.append(AddressCluster(members=members, score=score))
        return sorted(clusters, key=lambda c: c.score, reverse=True)

    @staticmethod
    def _similarity(a: AddressStats, b: AddressStats) -> float:
        sent_gap = abs(a.sent - b.sent)
        recv_gap = abs(a.received - b.received)
        denom = max(a.sent + b.sent + a.received + b.received, 1e-9)
        return 1.0 - ((sent_gap + recv_gap) / denom)

    @staticmethod
    def _score(stats: AddressStats) -> float:
        counterparty_weight = min(stats.unique_counterparties / 100, 1.0)
        flow_weight = min((stats.sent + stats.received) / 1000, 1.0)
        return 0.6 * flow_weight + 0.4 * counterparty_weight
