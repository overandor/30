"""Agent for processing off-chain intel feeds."""

from __future__ import annotations

from typing import Iterable, List

from tools.firecrawl_tools import IntelSignal, merge_intel, parse_intel


class IntelAgent:
    def __init__(self) -> None:
        self.signals: List[IntelSignal] = []

    def ingest(self, source: str, payload: str) -> IntelSignal:
        signal = parse_intel(source=source, payload=payload)
        self.signals.append(signal)
        return signal

    def consolidate(self) -> IntelSignal:
        if not self.signals:
            raise ValueError("No intel signals ingested")
        return merge_intel(self.signals)

    def filter_by_address(self, address: str) -> List[IntelSignal]:
        return [signal for signal in self.signals if address in signal.addresses]

    def sources(self) -> Iterable[str]:
        return (signal.source for signal in self.signals)
