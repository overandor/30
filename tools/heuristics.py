from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List

from .solana_tools import TokenTransfer


@dataclass
class AddressStats:
    address: str
    received: float
    sent: float
    unique_counterparties: int


@dataclass
class SuspicionFlag:
    address: str
    reason: str


class TransferHeuristics:
    @staticmethod
    def aggregate_balances(transfers: Iterable[TokenTransfer]) -> Dict[str, AddressStats]:
        sent: Dict[str, float] = defaultdict(float)
        received: Dict[str, float] = defaultdict(float)
        peers: Dict[str, set] = defaultdict(set)

        for transfer in transfers:
            sent[transfer.source] += transfer.amount
            received[transfer.destination] += transfer.amount
            peers[transfer.source].add(transfer.destination)
            peers[transfer.destination].add(transfer.source)

        addresses = set(sent) | set(received)
        return {
            addr: AddressStats(
                address=addr,
                received=received.get(addr, 0.0),
                sent=sent.get(addr, 0.0),
                unique_counterparties=len(peers.get(addr, set())),
            )
            for addr in addresses
        }

    @staticmethod
    def flag_suspicious_patterns(transfers: Iterable[TokenTransfer], min_round_trip: float = 10.0) -> List[SuspicionFlag]:
        balance_map = TransferHeuristics.aggregate_balances(transfers)
        flags: List[SuspicionFlag] = []
        for stats in balance_map.values():
            if stats.sent > 0 and stats.received > 0:
                ratio = stats.sent / max(stats.received, 1e-9)
                if 0.8 <= ratio <= 1.25 and stats.sent > min_round_trip:
                    flags.append(
                        SuspicionFlag(
                            address=stats.address,
                            reason="Near-symmetric inflow/outflow exceeding threshold",
                        )
                    )
            if stats.unique_counterparties > 50 and stats.sent > 0:
                flags.append(
                    SuspicionFlag(
                        address=stats.address,
                        reason="High-degree hub behavior across many counterparties",
                    )
                )
        return flags
