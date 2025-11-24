"""Deterministic heuristics for Solana risk detection."""

from __future__ import annotations

from typing import Dict, List

from tools.solana_tools import Transaction


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / float(denominator)


def program_concentration(program_touches: int, tx_count: int) -> float:
    return _ratio(program_touches, tx_count)


def sudden_outflow(inbound: int, outbound: int) -> float:
    if inbound == 0:
        return 0.0
    return _ratio(outbound, inbound)


def score_account(metrics: Dict[str, int]) -> float:
    conc = program_concentration(metrics["program_touches"], metrics["tx_count"])
    outflow = sudden_outflow(metrics["inbound_lamports"], metrics["outbound_lamports"])
    fee_load = _ratio(metrics["fees"], metrics["tx_count"])
    return min(1.0, conc * 0.4 + outflow * 0.4 + fee_load * 0.2)


def flag_transactions(transactions: List[Transaction], lamport_threshold: int = 1_000_000_000) -> List[Transaction]:
    return [tx for tx in transactions if tx.lamports >= lamport_threshold]
