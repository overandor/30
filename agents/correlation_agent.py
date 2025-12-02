"""Agent correlating on-chain evidence with off-chain intel."""

from __future__ import annotations

from typing import Dict, List

from tools.firecrawl_tools import IntelSignal
from tools.solana_tools import Transaction


class CorrelationAgent:
    def __init__(self) -> None:
        self.correlations: List[Dict[str, object]] = []

    def correlate(self, intel: IntelSignal, transactions: List[Transaction]) -> List[Dict[str, object]]:
        correlated: List[Dict[str, object]] = []
        intel_addresses = set(intel.addresses)
        for tx in transactions:
            overlap = intel_addresses & tx.involved_addresses()
            if overlap:
                correlated.append(
                    {
                        "signature": tx.signature,
                        "slot": tx.slot,
                        "hit_addresses": sorted(overlap),
                        "lamports": tx.lamports,
                        "programs": tx.programs,
                    }
                )
        self.correlations = correlated
        return correlated

    def high_value_hits(self, minimum_lamports: int) -> List[Dict[str, object]]:
        return [hit for hit in self.correlations if hit["lamports"] >= minimum_lamports]
