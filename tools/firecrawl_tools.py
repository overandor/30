"""Utilities for consuming off-chain intelligence feeds.

Functions in this module avoid network access; callers must provide raw text
payloads. The helpers extract indicators from the provided content and
normalize the shape for downstream agents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

BASE58_PATTERN = r"[1-9A-HJ-NP-Za-km-z]{32,44}"


@dataclass(frozen=True)
class IntelSignal:
    source: str
    addresses: Tuple[str, ...]
    links: Tuple[str, ...]
    summary: str


def _extract_links(text: str) -> List[str]:
    link_pattern = re.compile(r"https?://[\w\.-/]+", re.IGNORECASE)
    return link_pattern.findall(text)


def _extract_addresses(text: str) -> List[str]:
    address_pattern = re.compile(BASE58_PATTERN)
    return address_pattern.findall(text)


def parse_intel(source: str, payload: str, summary_limit: int = 280) -> IntelSignal:
    """Convert raw intel text into a normalized signal record.

    Args:
        source: Identifier for the intel feed.
        payload: Raw text content from the feed.
        summary_limit: Maximum length of the compact summary.

    Returns:
        IntelSignal capturing extracted addresses and links.
    """

    addresses = tuple(_extract_addresses(payload))
    links = tuple(_extract_links(payload))
    compact = payload.strip().replace("\n", " ")
    if len(compact) > summary_limit:
        compact = compact[: summary_limit - 3] + "..."
    return IntelSignal(source=source, addresses=addresses, links=links, summary=compact)


def merge_intel(signals: Sequence[IntelSignal]) -> IntelSignal:
    """Combine multiple intel signals into one consolidated view."""

    addresses: List[str] = []
    links: List[str] = []
    summaries: List[str] = []

    for signal in signals:
        addresses.extend(signal.addresses)
        links.extend(signal.links)
        summaries.append(f"[{signal.source}] {signal.summary}")

    dedup_addresses = tuple(dict.fromkeys(addresses))
    dedup_links = tuple(dict.fromkeys(links))
    merged_summary = " | ".join(summaries)
    return IntelSignal(
        source="merged",
        addresses=dedup_addresses,
        links=dedup_links,
        summary=merged_summary,
    )


def filter_by_address(signals: Iterable[IntelSignal], address: str) -> List[IntelSignal]:
    return [signal for signal in signals if address in signal.addresses]
