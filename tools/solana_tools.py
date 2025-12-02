import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


class SolanaRPCError(RuntimeError):
    """Raised when the Solana RPC returns an error payload."""


@dataclass
class RPCConfig:
    endpoint: str
    commitment: str = "confirmed"
    timeout: int = 10


class SolanaRPCClient:
    """Minimal Solana RPC client focused on deterministic forensic queries."""

    def __init__(self, config: RPCConfig):
        self.config = config

    def _post(self, method: str, params: List[Any]) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
        response = requests.post(
            self.config.endpoint,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=self.config.timeout,
        )
        result = response.json()
        if "error" in result:
            raise SolanaRPCError(result["error"])
        return result["result"]

    def get_balance(self, address: str) -> int:
        result = self._post("getBalance", [address, {"commitment": self.config.commitment}])
        return int(result.get("value", 0))

    def get_signatures(self, address: str, before: Optional[str] = None, limit: int = 1000) -> List[str]:
        args: Dict[str, Any] = {"limit": limit}
        if before:
            args["before"] = before
        result = self._post("getSignaturesForAddress", [address, args])
        return [item["signature"] for item in result]

    def get_transaction(self, signature: str) -> Dict[str, Any]:
        return self._post(
            "getTransaction",
            [signature, {"commitment": self.config.commitment, "encoding": "jsonParsed"}],
        )

    def stream_transactions(self, address: str, page_size: int = 1000, max_pages: int = 10) -> List[Dict[str, Any]]:
        signatures: List[str] = []
        before: Optional[str] = None
        for _ in range(max_pages):
            batch = self.get_signatures(address, before=before, limit=page_size)
            if not batch:
                break
            signatures.extend(batch)
            before = batch[-1]
        return [self.get_transaction(sig) for sig in signatures]


@dataclass
class TokenTransfer:
    source: str
    destination: str
    amount: float
    mint: str
    slot: int
    signature: str


class TransactionParser:
    """Parses Solana transactions into normalized token transfer events."""

    @staticmethod
    def extract_transfers(tx: Dict[str, Any]) -> List[TokenTransfer]:
        transfers: List[TokenTransfer] = []
        meta = tx.get("meta") or {}
        slot = tx.get("slot", 0)
        signature = tx.get("transaction", {}).get("signatures", ["unknown"])[0]

        for inner in meta.get("innerInstructions", []):
            for instruction in inner.get("instructions", []):
                program = instruction.get("program") or instruction.get("programId")
                if program != "spl-token":
                    continue
                parsed = instruction.get("parsed", {})
                info = parsed.get("info", {})
                amount = float(info.get("amount", 0)) / 1_000_000_000
                transfers.append(
                    TokenTransfer(
                        source=info.get("source", ""),
                        destination=info.get("destination", ""),
                        amount=amount,
                        mint=info.get("mint", ""),
                        slot=slot,
                        signature=signature,
                    )
                )
        return transfers
