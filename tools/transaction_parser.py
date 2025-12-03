"""Parser for extracting SPL token transfers with mint-aware scaling."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class TokenTransfer:
    mint: str
    source: str
    destination: str
    amount: Decimal
    raw_amount: int
    decimals: int
    program: str


class TransactionParser:
    def __init__(
        self,
        mint_decimals: Optional[Dict[str, int]] = None,
        mint_lookup: Optional[Callable[[str], Optional[int]]] = None,
    ) -> None:
        self.mint_decimals = mint_decimals or {}
        self.mint_lookup = mint_lookup

    def extract_transfers(self, transaction: Dict[str, Any]) -> List[TokenTransfer]:
        meta: Dict[str, Any] = transaction.get("meta", {}) or {}
        message: Dict[str, Any] = transaction.get("transaction", {}).get("message", {}) or {}
        account_keys: List[str] = message.get("accountKeys", []) or []

        decimals_by_mint, account_mint_map = self._collect_token_metadata(meta, account_keys)

        transfers: List[TokenTransfer] = []
        for instruction in self._all_instructions(message, meta):
            transfer = self._parse_instruction(instruction, decimals_by_mint, account_mint_map)
            if transfer:
                transfers.append(transfer)
        return transfers

    def _collect_token_metadata(
        self, meta: Dict[str, Any], account_keys: List[str]
    ) -> Tuple[Dict[str, int], Dict[str, str]]:
        decimals_by_mint: Dict[str, int] = {}
        account_mint_map: Dict[str, str] = {}
        for balance in meta.get("preTokenBalances", []) + meta.get("postTokenBalances", []):
            mint = balance.get("mint")
            decimals = balance.get("uiTokenAmount", {}).get("decimals")
            account_index = balance.get("accountIndex")
            if mint and decimals is not None:
                decimals_by_mint.setdefault(mint, int(decimals))
            if mint is not None and account_index is not None and 0 <= account_index < len(account_keys):
                account_mint_map[account_keys[account_index]] = mint
        return decimals_by_mint, account_mint_map

    def _parse_instruction(
        self,
        instruction: Dict[str, Any],
        decimals_by_mint: Dict[str, int],
        account_mint_map: Dict[str, str],
    ) -> Optional[TokenTransfer]:
        parsed = instruction.get("parsed")
        if not isinstance(parsed, dict):
            return None

        program = str(instruction.get("program", ""))
        parsed_type = parsed.get("type")
        if parsed_type not in {"transfer", "transferChecked"}:
            return None

        info = parsed.get("info", {}) or {}
        source = str(info.get("source") or info.get("authority") or "")
        destination = str(info.get("destination") or info.get("dest") or "")
        token_amount = info.get("tokenAmount")

        raw_amount = 0
        decimals_from_instruction: Optional[int] = None
        if isinstance(token_amount, dict) and "amount" in token_amount:
            raw_amount = int(token_amount.get("amount", 0))
            if "decimals" in token_amount and token_amount["decimals"] is not None:
                decimals_from_instruction = int(token_amount["decimals"])
        elif "amount" in info:
            raw_amount = int(info.get("amount", 0))
        else:
            return None

        mint = str(info.get("mint") or "")
        if not mint:
            mint = account_mint_map.get(source) or account_mint_map.get(destination) or ""
        if not mint:
            return None

        decimals = self._decimals_for_mint(mint, decimals_by_mint)
        if decimals_from_instruction is not None:
            decimals = decimals_from_instruction
        if decimals is None:
            return None

        amount = Decimal(raw_amount) / (Decimal(10) ** Decimal(decimals))
        return TokenTransfer(
            mint=mint,
            source=source,
            destination=destination,
            amount=amount,
            raw_amount=raw_amount,
            decimals=decimals,
            program=program,
        )

    def _decimals_for_mint(self, mint: str, decimals_by_mint: Dict[str, int]) -> Optional[int]:
        if mint in decimals_by_mint:
            return decimals_by_mint[mint]
        if mint in self.mint_decimals:
            return self.mint_decimals[mint]
        if self.mint_lookup:
            resolved = self.mint_lookup(mint)
            if resolved is not None:
                self.mint_decimals[mint] = resolved
            return resolved
        return None

    def _all_instructions(self, message: Dict[str, Any], meta: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        for instruction in message.get("instructions", []) or []:
            yield instruction
        for inner in meta.get("innerInstructions", []) or []:
            for instruction in inner.get("instructions", []) or []:
                yield instruction
