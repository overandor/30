# DEX Sniper Agent

A deterministic quote-comparison core for Solana DEX routing between Jupiter and Orca. The agent pulls quotes, evaluates price improvement against a reference, and produces an execution plan without handling key material or signing.

## Components
- `AgentConfig`, `PairConfig`, `StrategyConfig`: runtime configuration for endpoints, trade pair, and execution constraints.
- `DexSniperAgent`: orchestrates quote retrieval from Jupiter and Orca, then selects an execution path when price improvement and slippage conditions are satisfied.
- `SniperStrategy`: deterministic selector that enforces minimum improvement, output floors, and slippage ceilings.

## Usage
```python
from decimal import Decimal
from dex_sniper import AgentConfig, PairConfig, StrategyConfig, DexSniperAgent

agent = DexSniperAgent(
    agent_config=AgentConfig(),
    pair_config=PairConfig(
        in_mint="So11111111111111111111111111111111111111112",  # SOL
        out_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        amount_in=1_000_000,  # lamports
        slippage_bps=50,
    ),
    strategy_config=StrategyConfig(
        reference_price=Decimal("100"),
        min_improvement_bps=Decimal("25"),
        max_slippage_bps=100,
        min_out_amount=99_000_000,
    ),
)

decision, quotes = agent.plan()
if decision.execute:
    plan = agent.build_execution()
    print(plan.swap_endpoint, plan.request)
else:
    print(decision.reason)
```

`DexSniperAgent.fetch_quotes` returns quotes using HTTP GET calls to Jupiter and Orca. Signing, on-chain submission, and key management are intentionally excluded and must be provided by the caller.
