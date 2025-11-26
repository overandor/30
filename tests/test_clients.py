import unittest
from decimal import Decimal

from dex_sniper.agent import DexSniperAgent
from dex_sniper.config import AgentConfig, PairConfig, StrategyConfig
from dex_sniper.jupiter import JupiterClient
from dex_sniper.orca import OrcaClient


class JupiterClientTests(unittest.TestCase):
    def test_parse_quote_validates_and_extracts(self) -> None:
        client = JupiterClient("https://example.com")
        response = {
            "outAmount": "200",
            "routePlan": [
                {"swapInfo": {"ammKey": "route-amm"}}
            ],
        }

        quote = client.parse_quote(response, "A", "B", 100, 50)

        self.assertEqual(quote.out_amount, 200)
        self.assertEqual(quote.price, Decimal("2"))
        self.assertEqual(quote.context["best_route"], "route-amm")

    def test_parse_quote_rejects_missing_out_amount(self) -> None:
        client = JupiterClient("https://example.com")
        with self.assertRaises(ValueError):
            client.parse_quote({}, "A", "B", 100, 50)


class OrcaClientTests(unittest.TestCase):
    def test_parse_quote_validates_and_extracts(self) -> None:
        client = OrcaClient("https://example.com")
        response = {
            "quotedAmount": "150",
            "poolAddress": "pool-addr",
            "tickCurrentIndex": 42,
        }

        quote = client.parse_quote(response, "A", "B", 100, 50)

        self.assertEqual(quote.out_amount, 150)
        self.assertEqual(quote.price, Decimal("1.5"))
        self.assertEqual(quote.context["pool"], "pool-addr")
        self.assertEqual(quote.context["tick"], "42")

    def test_parse_quote_rejects_missing_quoted_amount(self) -> None:
        client = OrcaClient("https://example.com")
        with self.assertRaises(ValueError):
            client.parse_quote({}, "A", "B", 100, 50)


class AgentFetchQuotesTests(unittest.TestCase):
    class _FakeHttp:
        def __init__(self, responses):
            self.responses = responses
            self.calls = 0

        def get_json(self, url, params=None):
            response = self.responses[self.calls]
            self.calls += 1
            return response

    def test_fetch_quotes_skips_invalid_responses(self) -> None:
        agent = DexSniperAgent(
            agent_config=AgentConfig(jupiter_base_url="https://jup", orca_base_url="https://orca"),
            pair_config=PairConfig(in_mint="A", out_mint="B", amount_in=100, slippage_bps=50),
            strategy_config=StrategyConfig(reference_price=Decimal("1"), min_improvement_bps=Decimal("10"), max_slippage_bps=100),
        )
        agent.http = self._FakeHttp(
            responses=[
                {},
                {"quotedAmount": "120", "poolAddress": "p1", "tickCurrentIndex": 1},
            ]
        )

        quotes = agent.fetch_quotes()

        self.assertEqual(len(quotes), 1)
        self.assertEqual(quotes[0].aggregator, "orca")


if __name__ == "__main__":
    unittest.main()
