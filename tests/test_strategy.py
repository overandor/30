import unittest
from decimal import Decimal

from dex_sniper.config import StrategyConfig
from dex_sniper.models import Quote
from dex_sniper.strategy import SniperStrategy


class SniperStrategyTests(unittest.TestCase):
    def test_executes_when_improvement_and_slippage_ok(self) -> None:
        strategy = SniperStrategy(
            StrategyConfig(
                reference_price=Decimal("1.0"),
                min_improvement_bps=Decimal("50"),
                max_slippage_bps=100,
            )
        )
        quotes = [
            Quote(
                aggregator="jupiter",
                in_mint="A",
                out_mint="B",
                in_amount=100,
                out_amount=110,
                slippage_bps=75,
                price=Decimal("1.1"),
                context={},
            ),
            Quote(
                aggregator="orca",
                in_mint="A",
                out_mint="B",
                in_amount=100,
                out_amount=108,
                slippage_bps=50,
                price=Decimal("1.08"),
                context={},
            ),
        ]

        decision = strategy.evaluate(quotes)
        self.assertTrue(decision.execute)
        self.assertEqual(decision.aggregator, "jupiter")
        self.assertGreaterEqual(decision.improvement_bps, Decimal("50"))

    def test_rejects_when_improvement_too_low(self) -> None:
        strategy = SniperStrategy(
            StrategyConfig(
                reference_price=Decimal("1.0"),
                min_improvement_bps=Decimal("200"),
                max_slippage_bps=100,
            )
        )
        quote = Quote(
            aggregator="jupiter",
            in_mint="A",
            out_mint="B",
            in_amount=100,
            out_amount=101,
            slippage_bps=75,
            price=Decimal("1.01"),
            context={},
        )

        decision = strategy.evaluate([quote])
        self.assertFalse(decision.execute)
        self.assertEqual(decision.reason, "improvement below threshold")


if __name__ == "__main__":
    unittest.main()
