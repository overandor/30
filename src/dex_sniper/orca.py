from decimal import Decimal
from typing import Dict

from .models import Quote


class OrcaClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def quote_params(self, in_mint: str, out_mint: str, amount: int, slippage_bps: int) -> Dict[str, str]:
        return {
            "inputMint": in_mint,
            "outputMint": out_mint,
            "amount": str(amount),
            "slippageTolerance": str(Decimal(slippage_bps) / Decimal(10_000)),
            "amountSpecifiedIsInput": "true",
        }

    def parse_quote(self, response: Dict[str, object], in_mint: str, out_mint: str, amount: int, slippage_bps: int) -> Quote:
        quoted_amount = response["quotedAmount"]
        if not isinstance(quoted_amount, str):
            raise ValueError("Orca quote response missing quotedAmount")
        out_amount = int(quoted_amount)
        price = Decimal(out_amount) / Decimal(amount)
        pool_addr = response.get("poolAddress", "")
        context = {"pool": pool_addr, "tick": str(response.get("tickCurrentIndex", ""))}
        return Quote(
            aggregator="orca",
            in_mint=in_mint,
            out_mint=out_mint,
            in_amount=amount,
            out_amount=out_amount,
            slippage_bps=slippage_bps,
            price=price,
            context=context,
        )
