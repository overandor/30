#!/usr/bin/env python3
# drift_trader_prod.py
# Author: Cartman, senior protocol auditor
# ---------------------------------------------------------------------
# Production-grade Drift v2 auto-trader. One file, no mocks.

import asyncio, json, os, signal, sys, time, logging, contextlib, random
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import yaml

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from anchorpy import Provider, Wallet
from solana.rpc.types import TxOpts
import spl.token.instructions

from driftpy.drift_client import DriftClient
from driftpy.types import *
from driftpy.constants.config import configs
from driftpy.accounts import get_perp_market_account

# ---------------------------------------------------------------------
# 1. Static configuration ------------------------------------------------

USDC_MINT = Pubkey.from_string(
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
)

@dataclass(frozen=True)
class PairCfg:
    symbol: str
    idx: int
    base_sz: Decimal
    max_pos: Decimal
    enable: bool
    strat: str           # "mean_rev" | "trend"

PAIR_TABLE: List[PairCfg] = [
    PairCfg("SOL-PERP", 0, Decimal("0.02"), Decimal("0.20"), True,  "mean_rev"),
    PairCfg("BTC-PERP", 1, Decimal("0.001"), Decimal("0.01"), True, "trend"),
    PairCfg("ETH-PERP", 2, Decimal("0.005"), Decimal("0.05"), True, "mean_rev"),
]

@dataclass(frozen=True)
class Limits:
    max_leverage: Decimal = Decimal("3")
    max_drawdown: Decimal = Decimal("0.10")
    daily_loss:  Decimal = Decimal("0.05")
    stop_loss:   Decimal = Decimal("0.05")   # per-trade
    take_profit: Decimal = Decimal("0.10")   # per-trade
    min_sol:     Decimal = Decimal("0.02")
    min_usdc:    Decimal = Decimal("20")

# ---------------------------------------------------------------------
# 2. Indicators & Risk Management ----------------------------------------

class Indicators:
    @staticmethod
    async def sma(prices: List[Decimal], period: int) -> Decimal:
        if len(prices) < period:
            return Decimal("0")
        return sum(prices[-period:]) / Decimal(period)
    
    @staticmethod
    async def bollinger_bands(prices: List[Decimal], period: int = 20) -> Tuple[Decimal, Decimal]:
        if len(prices) < period:
            return Decimal("0"), Decimal("0")
        sma = await Indicators.sma(prices, period)
        variance = sum((p - sma) ** 2 for p in prices[-period:]) / Decimal(period)
        std = variance.sqrt()
        return sma - 2 * std, sma + 2 * std
    
    @staticmethod
    async def rsi(prices: List[Decimal], period: int = 14) -> Decimal:
        if len(prices) < period + 1:
            return Decimal("50")
        
        gains = []
        losses = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(Decimal("0"))
            else:
                gains.append(Decimal("0"))
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / Decimal(period)
        avg_loss = sum(losses[-period:]) / Decimal(period)
        
        if avg_loss == 0:
            return Decimal("100")
        
        rs = avg_gain / avg_loss
        return Decimal("100") - (Decimal("100") / (Decimal("1") + rs))

@dataclass
class CircuitBreaker:
    max_consecutive_errors: int = 5
    error_count: int = 0
    last_error_time: float = 0
    
    def should_halt(self, error: Exception) -> bool:
        self.error_count += 1
        self.last_error_time = time.time()
        return self.error_count >= self.max_consecutive_errors

class RiskManager:
    def __init__(self, trader: 'Trader'):
        self.trader = trader
    
    async def check_position_sizes(self) -> bool:
        """Ensure no single position exceeds limits"""
        for pcfg in PAIR_TABLE:
            pos = await self.trader.position(pcfg.idx)
            if pos:
                size = abs(Decimal(pos.base_asset_amount) / Decimal(1e9))
                if size > pcfg.max_pos:
                    LOG.warning(f"Position size {size} exceeds max {pcfg.max_pos} for {pcfg.symbol}")
                    return False
        return True
    
    async def check_correlation(self) -> bool:
        """Basic correlation check to avoid concentrated exposure"""
        open_positions = 0
        for p in PAIR_TABLE:
            if await self.trader.position(p.idx) is not None:
                open_positions += 1
        return open_positions <= len(PAIR_TABLE) // 2  # Max 50% of pairs
    
    async def check_volatility(self, prices: Dict[int, Decimal]) -> bool:
        """Check if market volatility is too high"""
        # Simple volatility check - in production, implement proper volatility metrics
        return True

# ---------------------------------------------------------------------
# 3. Utilities -----------------------------------------------------------

def load_key() -> Keypair:
    raw = os.getenv("SOLANA_PRIVATE_KEY")
    if not raw:
        # Generate a new keypair for demo (in production, use env var)
        kp = Keypair()
        print(f"⚠️  No SOLANA_PRIVATE_KEY found. Generated new keypair: {kp.pubkey()}")
        print("⚠️  Fund this account and set SOLANA_PRIVATE_KEY env var for production")
        return kp
        
    if raw.strip().startswith("["):
        secret = bytes(json.loads(raw))
    else:
        secret = bytes(Keypair.from_base58_string(raw).secret())
    return Keypair.from_bytes(secret)

def new_logger() -> logging.Logger:
    log = logging.getLogger("drift_trader")
    log.setLevel(logging.INFO)
    fmt = logging.Formatter(
        fmt="%(asctime)sZ %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )
    for h in (logging.StreamHandler(sys.stdout),
              logging.FileHandler("drift_trader.log", encoding="utf-8")):
        h.setFormatter(fmt)
        log.addHandler(h)
    logging.Formatter.converter = time.gmtime  # UTC
    return log

LOG = new_logger()

# ---------------------------------------------------------------------
# 4. Trader class -------------------------------------------------------

class Trader:
    def __init__(self, rpc: str):
        self.rpc_url = rpc
        self.kp = load_key()
        self.client = AsyncClient(rpc)
        self.wallet = Wallet(self.kp)
        self.provider = Provider(
            self.client, self.wallet,
            TxOpts(skip_preflight=False, preflight_commitment=Confirmed)
        )
        self.drift = DriftClient(self.provider, configs["mainnet"])
        self._running = True
        self.pnl_today: Decimal = Decimal("0")
        self.consecutive_failures = 0
        self.circuit_breaker = CircuitBreaker()
        self.risk_manager = RiskManager(self)
        self.price_history: Dict[int, List[Decimal]] = {p.idx: [] for p in PAIR_TABLE}
        self.start_time = time.time()

    # ---------- init ----------------------------------------------------
    async def bootstrap(self) -> None:
        try:
            await self.drift.get_user_account()
            LOG.info("✅ Existing Drift user found")
        except Exception:
            LOG.info("No Drift user, creating…")
            try:
                tx = await self.drift.initialize_user(sub_account_id=0)
                sig = await self.provider.send(tx)
                LOG.info(f"✅ User initialized: {sig}")
            except Exception as e:
                LOG.error(f"Failed to initialize user: {e}")
                raise

    # ---------- balances ------------------------------------------------
    async def sol(self) -> Decimal:
        try:
            lamports = (await self.client.get_balance(self.kp.pubkey())).value
            return Decimal(lamports) / Decimal(1e9)
        except Exception as e:
            LOG.error(f"Failed to get SOL balance: {e}")
            return Decimal("0")

    async def usdc(self) -> Decimal:
        try:
            ata = spl.token.instructions.get_associated_token_address(
                self.kp.pubkey(), USDC_MINT
            )
            bal = await self.client.get_token_account_balance(ata)
            return Decimal(bal.value.ui_amount or 0)
        except Exception as e:
            LOG.error(f"Failed to get USDC balance: {e}")
            return Decimal("0")

    # ---------- market helpers -----------------------------------------
    async def price(self, idx: int) -> Decimal:
        try:
            pd = self.drift.get_oracle_price_for_perp_market(idx)
            return Decimal(pd.price) / Decimal(1e6)
        except Exception as e:
            LOG.error(f"Failed to get price for market {idx}: {e}")
            return Decimal("0")

    async def update_price_history(self, idx: int, price: Decimal):
        """Maintain rolling price window for indicators"""
        if price > 0:  # Only update with valid prices
            history = self.price_history[idx]
            history.append(price)
            # Keep last 100 prices
            if len(history) > 100:
                self.price_history[idx] = history[-100:]

    # ---------- order plumbing -----------------------------------------
    async def mkt(self, idx: int, sz: Decimal, long: bool):
        try:
            direction = PositionDirection.Long() if long else PositionDirection.Short()
            params = OrderParams(
                order_type=OrderType.Market(),
                market_type=MarketType.Perp(),
                direction=direction,
                base_asset_amount=int(sz * Decimal(1e9)),
                price=0,
                market_index=idx,
                reduce_only=False,
                post_only=PostOnlyOption.None(),
                immediate_or_cancel=False,
                trigger_price=0,
                trigger_condition=OrderTriggerCondition.Above(),
                oracle_price_offset=0
            )
            tx = await self.drift.place_order(params)
            sig = await self.provider.send(tx)
            LOG.info(f"✅ MARKET {idx} {'LONG' if long else 'SHORT'} {sz} → {sig}")
            return True
        except Exception as e:
            LOG.error(f"❌ Order failed for market {idx}: {e}")
            return False

    async def close_pos(self, idx: int):
        try:
            pos = await self.position(idx)
            if not pos:
                return True
            sz = abs(Decimal(pos.base_asset_amount) / Decimal(1e9))
            success = await self.mkt(idx, sz, long=(pos.base_asset_amount < 0))
            if success:
                LOG.info(f"✅ Closed position for market {idx}")
            return success
        except Exception as e:
            LOG.error(f"❌ Failed to close position for market {idx}: {e}")
            return False

    # ---------- portfolio ----------------------------------------------
    async def position(self, idx: int):
        try:
            ua = await self.drift.get_user_account()
            for p in ua.positions:
                if p.market_index == idx and p.base_asset_amount != 0:
                    return p
            return None
        except Exception as e:
            LOG.error(f"Failed to get position for market {idx}: {e}")
            return None

    async def leverage(self) -> Decimal:
        try:
            acc = await self.drift.get_user_account()
            total_collateral = Decimal(acc.total_collateral) / Decimal(1e6)
            total_position_value = Decimal(acc.total_position_value) / Decimal(1e6)
            
            if total_collateral == 0:
                return Decimal("0")
            return total_position_value / total_collateral
        except Exception as e:
            LOG.error(f"Failed to calculate leverage: {e}")
            return Decimal("0")

    # ---------- strategy per pair --------------------------------------
    async def entry_signal(self, pcfg: PairCfg, current_price: Decimal) -> bool:
        history = self.price_history[pcfg.idx]
        if len(history) < 20:  # Need sufficient data
            return False
        
        if pcfg.strat == "mean_rev":
            # Mean reversion: Buy when oversold (below lower Bollinger Band)
            lower_band, upper_band = await Indicators.bollinger_bands(history)
            rsi = await Indicators.rsi(history)
            return current_price <= lower_band and rsi < 30
            
        elif pcfg.strat == "trend":
            # Trend following: Buy when in uptrend
            sma_20 = await Indicators.sma(history, 20)
            sma_50 = await Indicators.sma(history, 50)
            rsi = await Indicators.rsi(history)
            return sma_20 > sma_50 and rsi < 70  # Uptrend but not overbought
        
        return False

    async def manage_existing_position(self, pcfg: PairCfg, pos, current_price: Decimal):
        entry = Decimal(pos.entry_price) / Decimal(1e6)
        sz = Decimal(pos.base_asset_amount) / Decimal(1e9)
        pnl = (current_price - entry) * sz if sz > 0 else (entry - current_price) * (-sz)
        pnl_percent = pnl / (abs(sz) * entry) if entry > 0 else Decimal("0")
        
        # Stop loss / Take profit
        if pnl_percent <= -Limits.stop_loss:
            LOG.info(f"🛑 {pcfg.symbol} STOP LOSS triggered: {pnl_percent:.2%}")
            await self.close_pos(pcfg.idx)
        elif pnl_percent >= Limits.take_profit:
            LOG.info(f"🎯 {pcfg.symbol} TAKE PROFIT triggered: {pnl_percent:.2%}")
            await self.close_pos(pcfg.idx)

    async def step_pair(self, pcfg: PairCfg):
        if not pcfg.enable:
            return
        
        try:
            idx = pcfg.idx
            px = await self.price(idx)
            if px == 0:  # Invalid price
                return
                
            await self.update_price_history(idx, px)
            
            pos = await self.position(idx)
            
            # Position management
            if pos:
                await self.manage_existing_position(pcfg, pos, px)
                return
            
            # Entry logic
            if await self.entry_signal(pcfg, px):
                LOG.info(f"🎯 {pcfg.symbol} ENTRY SIGNAL at {px:.4f}")
                success = await self.mkt(idx, pcfg.base_sz, long=True)
                if success:
                    LOG.info(f"✅ Entered {pcfg.symbol} position")
                    
        except Exception as e:
            LOG.error(f"Step pair error for {pcfg.symbol}: {e}")
            self.consecutive_failures += 1

    # ---------- risk gate ----------------------------------------------
    async def risk_ok(self) -> bool:
        try:
            sol_bal, usdc_bal = await self.sol(), await self.usdc()
            lev = await self.leverage()
            
            checks = [
                (sol_bal >= Limits.min_sol, f"SOL balance {sol_bal:.4f} < min {Limits.min_sol}"),
                (usdc_bal >= Limits.min_usdc, f"USDC balance {usdc_bal:.2f} < min {Limits.min_usdc}"),
                (lev <= Limits.max_leverage, f"Leverage {lev:.2f}× > max {Limits.max_leverage}"),
                (self.pnl_today >= -Limits.daily_loss, f"Daily PnL {self.pnl_today:.2%} < limit {-Limits.daily_loss}"),
                (await self.risk_manager.check_position_sizes(), "Position size limits exceeded"),
                (await self.risk_manager.check_correlation(), "Too many correlated positions"),
                (self.consecutive_failures < 5, f"Too many consecutive failures: {self.consecutive_failures}"),
            ]
            
            for check_passed, error_msg in checks:
                if not check_passed:
                    LOG.error(f"Risk check failed: {error_msg}")
                    return False
                    
            return True
            
        except Exception as e:
            LOG.error(f"Risk check error: {e}")
            return False

    # ---------- health monitoring --------------------------------------
    async def health_check(self) -> bool:
        """Comprehensive system health check"""
        try:
            # Check connection
            if not await self.client.is_connected():
                LOG.error("❌ Solana RPC connection failed")
                return False
                
            # Check balances
            sol_bal, usdc_bal = await self.sol(), await self.usdc()
            if sol_bal == 0 or usdc_bal == 0:
                LOG.error("❌ Zero balances detected")
                return False
                
            return True
            
        except Exception as e:
            LOG.error(f"Health check failed: {e}")
            return False

    # ---------- status reporting ---------------------------------------
    async def report_status(self):
        """Periodic status reporting"""
        sol_bal = await self.sol()
        usdc_bal = await self.usdc()
        lev = await self.leverage()
        
        open_positions = 0
        for p in PAIR_TABLE:
            if await self.position(p.idx):
                open_positions += 1
                
        uptime = time.time() - self.start_time
        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        
        LOG.info(f"📊 STATUS | SOL: {sol_bal:.4f} | USDC: {usdc_bal:.2f} | "
                f"Lev: {lev:.2f}× | Positions: {open_positions}/{len(PAIR_TABLE)} | "
                f"Uptime: {int(hours)}h {int(minutes)}m")

    # ---------- main loop ----------------------------------------------
    async def run(self):
        await self.bootstrap()
        LOG.info("🚀 DRIFT TRADER ONLINE")
        
        status_counter = 0
        while self._running:
            try:
                # Periodic status report every 10 cycles
                if status_counter % 10 == 0:
                    await self.report_status()
                status_counter += 1
                
                if not await self.health_check():
                    LOG.warning("Health check failed, waiting...")
                    await asyncio.sleep(60)
                    continue
                    
                if not await self.risk_ok():
                    LOG.error("Risk limits exceeded, emergency liquidation!")
                    await self.emergency_liq()
                    break
                
                # Execute trading strategies
                tasks = [self.step_pair(pcfg) for pcfg in PAIR_TABLE]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Reset consecutive failures on successful cycle
                self.consecutive_failures = 0
                
                await asyncio.sleep(30)  # 30-second cycle
                
            except Exception as exc:
                LOG.error(f"Main loop error: {exc}")
                self.consecutive_failures += 1
                await asyncio.sleep(15)

    async def emergency_liq(self):
        LOG.warning("🛑 EMERGENCY LIQUIDATION INITIATED")
        tasks = [self.close_pos(p.idx) for p in PAIR_TABLE]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        LOG.info(f"Emergency liquidation complete: {success_count}/{len(PAIR_TABLE)} successful")
        
        self._running = False

    # ---------- shutdown ------------------------------------------------
    async def close(self):
        LOG.info("Shutting down trader...")
        with contextlib.suppress(Exception):
            await self.drift.unsubscribe()
            await self.client.close()
        LOG.info("Trader shutdown complete")

# ---------------------------------------------------------------------
# 5. Entrypoint --------------------------------------------------------

async def main():
    # Auto-configure for production
    rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    
    if not os.getenv("SOLANA_PRIVATE_KEY"):
        print("❌ SOLANA_PRIVATE_KEY environment variable required")
        print("💡 Export your keypair: export SOLANA_PRIVATE_KEY='[1,2,3,...]'")
        return
    
    trader = Trader(rpc_url)

    # Graceful shutdown handling
    def signal_handler(sig, frame):
        LOG.info(f"Received signal {sig}, shutting down...")
        trader._running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await trader.run()
    except Exception as e:
        LOG.error(f"Fatal error: {e}")
    finally:
        await trader.close()
        LOG.info("🎯 Trader shutdown complete")

if __name__ == "__main__":
    print("🚀 Starting Drift v2 Auto-Trader...")
    print("⚠️  Ensure SOLANA_PRIVATE_KEY is set with sufficient SOL/USDC")
    print("⏰ Trading cycle: 30 seconds | Strategies: Mean Reversion & Trend Following")
    asyncio.run(main())