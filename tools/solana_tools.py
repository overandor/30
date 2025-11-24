"""Solana-centric helpers for deterministic offline analysis."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Set

BASE58_ALPHABET = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")


@dataclass(frozen=True)
class Transaction:
    signature: str
    slot: int
    signer: str
    accounts: List[str]
    programs: List[str]
    lamports: int
    fee: int

    def involved_addresses(self) -> Set[str]:
        return set(self.accounts) | {self.signer}


def is_valid_address(address: str, min_len: int = 32, max_len: int = 44) -> bool:
    if not (min_len <= len(address) <= max_len):
        return False
    return all(ch in BASE58_ALPHABET for ch in address)


def parse_transaction(record: Dict[str, object]) -> Transaction:
    signature = str(record["signature"])
    slot = int(record["slot"])
    signer = str(record["signer"])
    accounts = [str(addr) for addr in record.get("accounts", [])]
    programs = [str(pid) for pid in record.get("programs", [])]
    lamports = int(record.get("lamports", 0))
    fee = int(record.get("fee", 0))
    return Transaction(
        signature=signature,
        slot=slot,
        signer=signer,
        accounts=accounts,
        programs=programs,
        lamports=lamports,
        fee=fee,
    )


def hash_transaction(tx: Transaction) -> str:
    digest = hashlib.sha3_256()
    digest.update(tx.signature.encode())
    digest.update(str(tx.slot).encode())
    digest.update(tx.signer.encode())
    digest.update(";".join(tx.accounts).encode())
    digest.update(";".join(tx.programs).encode())
    digest.update(str(tx.lamports).encode())
    digest.update(str(tx.fee).encode())
    return digest.hexdigest()


def summarize_accounts(transactions: Sequence[Transaction]) -> Dict[str, Dict[str, int]]:
    summary: Dict[str, Dict[str, int]] = {}
    for tx in transactions:
        participants = tx.involved_addresses()
        for address in participants:
            if address not in summary:
                summary[address] = {
                    "slots": 0,
                    "inbound_lamports": 0,
                    "outbound_lamports": 0,
                    "fees": 0,
                    "program_touches": 0,
                    "tx_count": 0,
                }
            record = summary[address]
            record["slots"] = max(record["slots"], tx.slot)
            record["fees"] += tx.fee
            record["program_touches"] += len(tx.programs)
            record["tx_count"] += 1
            if address == tx.signer:
                record["outbound_lamports"] += tx.lamports
            else:
                record["inbound_lamports"] += tx.lamports
    return summary


def normalize_address(address: str) -> str:
    return address.strip()


def filter_transactions(transactions: Iterable[Transaction], address: str) -> List[Transaction]:
    normalized = normalize_address(address)
    return [tx for tx in transactions if normalized in tx.involved_addresses()]
