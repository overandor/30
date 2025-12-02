from dataclasses import dataclass
from typing import Dict, List

from tools.clustering import AddressCluster
from tools.heuristics import AddressStats, SuspicionFlag
from tools.solana_tools import TokenTransfer


@dataclass
class Report:
    summary: Dict[str, str]
    balances: List[AddressStats]
    flags: List[SuspicionFlag]
    clusters: List[AddressCluster]
    transfers: List[TokenTransfer]


class ReportAgent:
    @staticmethod
    def build(balances: Dict[str, AddressStats], flags: List[SuspicionFlag], clusters: List[AddressCluster], transfers: List[TokenTransfer]) -> Report:
        top_flags = sorted(flags, key=lambda f: f.address)
        top_clusters = clusters[:10]
        summary = {
            "flagged_addresses": str(len(top_flags)),
            "cluster_count": str(len(clusters)),
            "transfer_count": str(len(transfers)),
        }
        return Report(
            summary=summary,
            balances=list(balances.values()),
            flags=top_flags,
            clusters=top_clusters,
            transfers=transfers,
        )

    @staticmethod
    def to_text(report: Report) -> str:
        lines: List[str] = [
            "Solana Forensic Report",
            "======================",
            f"Flagged addresses: {report.summary['flagged_addresses']}",
            f"Clusters: {report.summary['cluster_count']}",
            f"Transfers analyzed: {report.summary['transfer_count']}",
            "",
            "Suspicious addresses:",
        ]
        for flag in report.flags:
            lines.append(f"- {flag.address}: {flag.reason}")
        lines.append("")
        lines.append("Top clusters:")
        for cluster in report.clusters:
            members = ", ".join(sorted(cluster.members))
            lines.append(f"- score={cluster.score:.3f} members={members}")
        return "\n".join(lines)
