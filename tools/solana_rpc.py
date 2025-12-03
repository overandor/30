"""Resilient Solana RPC helper with explicit error mapping."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass
class SolanaRPCError(Exception):
    """Domain error that carries HTTP context for RPC failures."""

    message: str
    http_status: Optional[int] = None
    body: Optional[str] = None
    cause: Optional[BaseException] = None

    def __str__(self) -> str:  # pragma: no cover - representational only
        suffix = []
        if self.http_status is not None:
            suffix.append(f"status={self.http_status}")
        if self.body:
            suffix.append(f"body={self.body}")
        if self.cause:
            suffix.append(f"cause={self.cause}")
        detail = ", ".join(suffix)
        return f"{self.message} ({detail})" if detail else self.message


class SolanaRPCClient:
    def __init__(self, endpoint: str, timeout: float = 10.0) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = self.session.post(self.endpoint, json=payload, timeout=self.timeout)
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise SolanaRPCError("RPC request failed", cause=exc) from exc

        status = response.status_code
        if status != 200:
            raise SolanaRPCError(
                "RPC request returned non-200 status",
                http_status=status,
                body=response.text,
            )

        try:
            return response.json()
        except ValueError as exc:
            raise SolanaRPCError(
                "RPC response was not valid JSON",
                http_status=status,
                body=response.text,
                cause=exc,
            ) from exc
