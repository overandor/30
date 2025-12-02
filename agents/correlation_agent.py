from dataclasses import dataclass
from typing import List

from tools.clustering import AddressCluster, GraphClusterer
from tools.heuristics import AddressStats, SuspicionFlag
from tools.solana_tools import TokenTransfer


@dataclass
class CorrelationResult:
    clusters: List[AddressCluster]
    flags: List[SuspicionFlag]


class CorrelationAgent:
    def __init__(self, similarity_threshold: float = 0.55):
        self.clusterer = GraphClusterer(similarity_threshold=similarity_threshold)

    def correlate(
        self,
        balances: List[AddressStats],
        flags: List[SuspicionFlag],
        transfers: List[TokenTransfer],
    ) -> CorrelationResult:
        clusters = self.clusterer.cluster_by_flow_similarity(balances)
        suspicious_addresses = {flag.address for flag in flags}
        propagated_flags: List[SuspicionFlag] = list(flags)

        for cluster in clusters:
            if cluster.members & suspicious_addresses:
                for addr in cluster.members:
                    if addr not in suspicious_addresses:
                        propagated_flags.append(
                            SuspicionFlag(
                                address=addr,
                                reason="Cluster proximity to flagged counterparties",
                            )
                        )
        return CorrelationResult(clusters=clusters, flags=propagated_flags)
