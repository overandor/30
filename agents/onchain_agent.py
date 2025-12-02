from dataclasses import dataclass
from typing import List

from tools.heuristics import TransferHeuristics
from tools.solana_tools import SolanaRPCClient, TokenTransfer, TransactionParser


@dataclass
class OnchainFinding:
    address: str
    transfers: List[TokenTransfer]


class OnchainAgent:
    def __init__(self, rpc_client: SolanaRPCClient):
        self.rpc_client = rpc_client

    def collect_transfers(self, addresses: List[str]) -> List[OnchainFinding]:
        findings: List[OnchainFinding] = []
        for address in addresses:
            txs = self.rpc_client.stream_transactions(address)
            transfers: List[TokenTransfer] = []
            for tx in txs:
                transfers.extend(TransactionParser.extract_transfers(tx))
            findings.append(OnchainFinding(address=address, transfers=transfers))
        return findings

    def summarize(self, findings: List[OnchainFinding]):
        all_transfers: List[TokenTransfer] = []
        for finding in findings:
            all_transfers.extend(finding.transfers)
        balances = TransferHeuristics.aggregate_balances(all_transfers)
        flags = TransferHeuristics.flag_suspicious_patterns(all_transfers)
        return {"balances": balances, "flags": flags, "transfers": all_transfers}
