from decimal import Decimal
from typing import Dict

from .models import Quote


class JupiterClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def quote_params(self, in_mint: str, out_mint: str, amount: int, slippage_bps: int) -> Dict[str, str]:
        return {
            "inputMint": in_mint,
            "outputMint": out_mint,
            "amount": str(amount),
            "slippageBps": str(slippage_bps),
            "swapMode": "ExactIn",
            "onlyDirectRoutes": "true",
        }

    def parse_quote(self, response: Dict[str, object], in_mint: str, out_mint: str, amount: int, slippage_bps: int) -> Quote:
        out_amount = int(response["outAmount"])
        price = Decimal(out_amount) / Decimal(amount)
        route_plan = response.get("routePlan", [])
        context = {"best_route": route_plan[0]["swapInfo"]["ammKey"] if route_plan else ""}
        return Quote(
            aggregator="jupiter",
            in_mint=in_mint,
            out_mint=out_mint,
            in_amount=amount,
            out_amount=out_amount,
            slippage_bps=slippage_bps,
            price=price,
            context=context,
        )
