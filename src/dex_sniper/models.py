from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional


@dataclass(frozen=True)
class Quote:
    aggregator: str
    in_mint: str
    out_mint: str
    in_amount: int
    out_amount: int
    slippage_bps: int
    price: Decimal
    context: Dict[str, str]


@dataclass(frozen=True)
class SniperDecision:
    execute: bool
    aggregator: Optional[str]
    improvement_bps: Decimal
    reference_price: Decimal
    reason: str
    selected_quote: Optional[Quote]
