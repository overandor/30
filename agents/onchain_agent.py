"""Agent for deterministic on-chain Solana inspection."""

from __future__ import annotations

from typing import Dict, Iterable, List

from tools import heuristics
from tools.clustering import build_clusters, cluster_summary
from tools.solana_tools import Transaction, filter_transactions, parse_transaction, summarize_accounts


class OnChainAgent:
    def __init__(self) -> None:
        self.transactions: List[Transaction] = []
        self.account_summary: Dict[str, Dict[str, int]] = {}
        self.clusters: List[Dict[str, object]] = []

    def ingest(self, records: Iterable[Dict[str, object]]) -> List[Transaction]:
        for record in records:
            tx = parse_transaction(record)
            self.transactions.append(tx)
        self.account_summary = summarize_accounts(self.transactions)
        self.clusters = cluster_summary(build_clusters(self.account_summary))
        return self.transactions

    def risky_transactions(self, lamport_threshold: int = 1_000_000_000) -> List[Transaction]:
        return heuristics.flag_transactions(self.transactions, lamport_threshold=lamport_threshold)

    def score_accounts(self) -> Dict[str, float]:
        if not self.account_summary:
            self.account_summary = summarize_accounts(self.transactions)
        return {address: heuristics.score_account(metrics) for address, metrics in self.account_summary.items()}

    def history_for(self, address: str) -> List[Transaction]:
        return filter_transactions(self.transactions, address)

    def metrics_for(self, address: str) -> Dict[str, int]:
        return self.account_summary.get(address, {})
