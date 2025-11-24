from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional

from .config import StrategyConfig
from .models import Quote, SniperDecision


@dataclass
class SniperState:
    reference_price: Decimal


class SniperStrategy:
    def __init__(self, config: StrategyConfig) -> None:
        self.config = config
        self.state = SniperState(reference_price=config.reference_price)

    def best_quote(self, quotes: Iterable[Quote]) -> Optional[Quote]:
        best: Optional[Quote] = None
        for quote in quotes:
            if best is None or quote.out_amount > best.out_amount:
                best = quote
        return best

    def improvement_bps(self, candidate_price: Decimal) -> Decimal:
        try:
            delta = candidate_price - self.state.reference_price
            return (delta / self.state.reference_price) * Decimal(10_000)
        except (InvalidOperation, ZeroDivisionError):
            return Decimal(0)

    def evaluate(self, quotes: Iterable[Quote]) -> SniperDecision:
        quote = self.best_quote(quotes)
        if quote is None:
            return SniperDecision(
                execute=False,
                aggregator=None,
                improvement_bps=Decimal(0),
                reference_price=self.state.reference_price,
                reason="no quotes available",
                selected_quote=None,
            )

        if quote.slippage_bps > self.config.max_slippage_bps:
            return SniperDecision(
                execute=False,
                aggregator=quote.aggregator,
                improvement_bps=Decimal(0),
                reference_price=self.state.reference_price,
                reason="slippage above limit",
                selected_quote=quote,
            )

        if self.config.min_out_amount is not None and quote.out_amount < self.config.min_out_amount:
            return SniperDecision(
                execute=False,
                aggregator=quote.aggregator,
                improvement_bps=Decimal(0),
                reference_price=self.state.reference_price,
                reason="expected output below floor",
                selected_quote=quote,
            )

        improvement = self.improvement_bps(quote.price)
        if improvement < self.config.min_improvement_bps:
            return SniperDecision(
                execute=False,
                aggregator=quote.aggregator,
                improvement_bps=improvement,
                reference_price=self.state.reference_price,
                reason="improvement below threshold",
                selected_quote=quote,
            )

        self.state.reference_price = quote.price
        return SniperDecision(
            execute=True,
            aggregator=quote.aggregator,
            improvement_bps=improvement,
            reference_price=self.state.reference_price,
            reason="exceeds improvement threshold",
            selected_quote=quote,
        )
