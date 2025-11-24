"""Agent generating consolidated forensic reports."""

from __future__ import annotations

from typing import Dict, List

from tools.firecrawl_tools import IntelSignal
from tools.solana_tools import Transaction


class ReportAgent:
    def build(self, *, intel: IntelSignal, correlations: List[Dict[str, object]], account_scores: Dict[str, float], clusters: List[Dict[str, object]]) -> Dict[str, object]:
        return {
            "intel_summary": intel.summary,
            "intel_addresses": list(intel.addresses),
            "correlations": correlations,
            "account_scores": account_scores,
            "clusters": clusters,
        }

    def to_text(self, report: Dict[str, object]) -> str:
        lines = ["Intel Summary:", report["intel_summary"], "", "Correlated Transactions:"]
        for hit in report["correlations"]:
            lines.append(
                f"- sig={hit['signature']} slot={hit['slot']} lamports={hit['lamports']} addresses={','.join(hit['hit_addresses'])}"
            )
        lines.append("")
        lines.append("Account Scores:")
        for addr, score in sorted(report["account_scores"].items(), key=lambda item: item[1], reverse=True):
            lines.append(f"- {addr}: score={score:.2f}")
        lines.append("")
        lines.append("Clusters:")
        for cluster in report["clusters"]:
            lines.append(f"- size={cluster['size']} members={','.join(cluster['members'])}")
        return "\n".join(lines)
