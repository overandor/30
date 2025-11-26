from decimal import Decimal, InvalidOperation
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
        if "outAmount" not in response:
            raise ValueError("Jupiter quote response missing outAmount")

        try:
            out_amount = int(response["outAmount"])
        except (TypeError, ValueError):
            raise ValueError("Jupiter outAmount is not parseable as int") from None

        try:
            price = Decimal(out_amount) / Decimal(amount)
        except (InvalidOperation, ZeroDivisionError):
            raise ValueError("Jupiter price computation failed") from None

        route_plan = response.get("routePlan", [])
        best_route = ""
        if route_plan:
            swap_info = route_plan[0].get("swapInfo") if isinstance(route_plan[0], dict) else None
            best_route = swap_info.get("ammKey", "") if isinstance(swap_info, dict) else ""
        context = {"best_route": best_route}
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
