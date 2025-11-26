from dataclasses import dataclass
from typing import List, Tuple

from requests import RequestException

from .config import AgentConfig, PairConfig, StrategyConfig
from .http_client import HttpClient
from .jupiter import JupiterClient
from .models import Quote, SniperDecision
from .orca import OrcaClient
from .strategy import SniperStrategy


@dataclass
class ExecutionPlan:
    decision: SniperDecision
    request: Quote
    swap_endpoint: str


class DexSniperAgent:
    def __init__(self, agent_config: AgentConfig, pair_config: PairConfig, strategy_config: StrategyConfig) -> None:
        self.agent_config = agent_config
        self.pair_config = pair_config
        self.http = HttpClient(timeout=agent_config.request_timeout, max_retries=agent_config.retries, user_agent="dex-sniper/1.0")
        self.jupiter = JupiterClient(agent_config.jupiter_base_url)
        self.orca = OrcaClient(agent_config.orca_base_url)
        self.strategy = SniperStrategy(strategy_config)

    def fetch_quotes(self) -> List[Quote]:
        quotes: List[Quote] = []
        params = self.jupiter.quote_params(
            in_mint=self.pair_config.in_mint,
            out_mint=self.pair_config.out_mint,
            amount=self.pair_config.amount_in,
            slippage_bps=self.pair_config.slippage_bps,
        )
        try:
            jupiter_resp = self.http.get_json(f"{self.agent_config.jupiter_base_url}/quote", params=params)
            quotes.append(
                self.jupiter.parse_quote(
                    jupiter_resp,
                    in_mint=self.pair_config.in_mint,
                    out_mint=self.pair_config.out_mint,
                    amount=self.pair_config.amount_in,
                    slippage_bps=self.pair_config.slippage_bps,
                )
            )
        except (RequestException, ValueError):
            pass

        orca_params = self.orca.quote_params(
            in_mint=self.pair_config.in_mint,
            out_mint=self.pair_config.out_mint,
            amount=self.pair_config.amount_in,
            slippage_bps=self.pair_config.slippage_bps,
        )
        try:
            orca_resp = self.http.get_json(f"{self.agent_config.orca_base_url}/whirlpool/quote", params=orca_params)
            quotes.append(
                self.orca.parse_quote(
                    orca_resp,
                    in_mint=self.pair_config.in_mint,
                    out_mint=self.pair_config.out_mint,
                    amount=self.pair_config.amount_in,
                    slippage_bps=self.pair_config.slippage_bps,
                )
            )
        except (RequestException, ValueError):
            pass

        return quotes

    def plan(self) -> Tuple[SniperDecision, List[Quote]]:
        quotes = self.fetch_quotes()
        decision = self.strategy.evaluate(quotes)
        return decision, quotes

    def build_execution(self) -> ExecutionPlan:
        decision, quotes = self.plan()
        if not decision.execute or decision.selected_quote is None:
            raise ValueError(f"execution not permitted: {decision.reason}")

        if decision.aggregator == "jupiter":
            endpoint = f"{self.agent_config.jupiter_base_url}/swap"
        elif decision.aggregator == "orca":
            endpoint = f"{self.agent_config.orca_base_url}/whirlpool/swap"
        else:
            raise ValueError("unknown aggregator in decision")

        return ExecutionPlan(decision=decision, request=decision.selected_quote, swap_endpoint=endpoint)
