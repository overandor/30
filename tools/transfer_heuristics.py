"""Mint-aware transfer aggregation and suspicion heuristics."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Iterable, List, Set

from tools.transaction_parser import TokenTransfer


@dataclass
class BalanceAggregate:
    sent: Decimal = Decimal(0)
    received: Decimal = Decimal(0)
    peers: Set[str] = field(default_factory=set)


@dataclass
class SuspiciousReport:
    by_mint: Dict[str, Dict[str, List[str]]]
    cross_mint: Dict[str, List[str]]


class TransferHeuristics:
    def __init__(self, round_trip_ratio: Decimal = Decimal("0.8"), hub_threshold: int = 6) -> None:
        self.round_trip_ratio = round_trip_ratio
        self.hub_threshold = hub_threshold

    def aggregate_balances(self, transfers: Iterable[TokenTransfer]) -> Dict[str, Dict[str, BalanceAggregate]]:
        buckets: Dict[str, Dict[str, BalanceAggregate]] = {}
        for transfer in transfers:
            mint_bucket = buckets.setdefault(transfer.mint, {})

            sender = mint_bucket.setdefault(transfer.source, BalanceAggregate())
            sender.sent += transfer.amount
            sender.peers.add(transfer.destination)

            receiver = mint_bucket.setdefault(transfer.destination, BalanceAggregate())
            receiver.received += transfer.amount
            receiver.peers.add(transfer.source)
        return buckets

    def flag_suspicious_patterns(
        self, aggregates: Dict[str, Dict[str, BalanceAggregate]]
    ) -> SuspiciousReport:
        by_mint: Dict[str, Dict[str, List[str]]] = {}
        cross_mint: Dict[str, List[str]] = {}
        for mint, address_map in aggregates.items():
            mint_flags: Dict[str, List[str]] = {}
            for address, metrics in address_map.items():
                reasons: List[str] = []
                if metrics.received > 0 and metrics.sent / metrics.received >= self.round_trip_ratio:
                    reasons.append("round_trip_flow")
                if len(metrics.peers) >= self.hub_threshold:
                    reasons.append("hub_like_behavior")
                if reasons:
                    mint_flags[address] = reasons
                    cross_reasons = cross_mint.setdefault(address, [])
                    cross_reasons.extend(f"{mint}:{reason}" for reason in reasons)
            if mint_flags:
                by_mint[mint] = mint_flags
        return SuspiciousReport(by_mint=by_mint, cross_mint=cross_mint)
