from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class PairConfig:
    in_mint: str
    out_mint: str
    amount_in: int
    slippage_bps: int


@dataclass(frozen=True)
class StrategyConfig:
    reference_price: Decimal
    min_improvement_bps: Decimal
    max_slippage_bps: int
    min_out_amount: Optional[int] = None


@dataclass(frozen=True)
class AgentConfig:
    jupiter_base_url: str = "https://quote-api.jup.ag/v6"
    orca_base_url: str = "https://api.orca.so/v1"
    request_timeout: float = 5.0
    retries: int = 3
