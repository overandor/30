from decimal import Decimal, InvalidOperation
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
        quoted_amount = response.get("quotedAmount")
        if quoted_amount is None:
            raise ValueError("Orca quote response missing quotedAmount")

        try:
            out_amount = int(quoted_amount)
        except (TypeError, ValueError):
            raise ValueError("Orca quotedAmount is not parseable as int") from None

        try:
            price = Decimal(out_amount) / Decimal(amount)
        except (InvalidOperation, ZeroDivisionError):
            raise ValueError("Orca price computation failed") from None

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
