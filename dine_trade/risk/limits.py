"""Risk limits and circuit breakers.

Includes:
- price_vs_ma_allowed: hard MA deviation constraint (anti-hallucination).
- Daily drawdown circuit breaker helper (to 1.5% or configured limit).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Tuple

from dine_trade.config.settings import DAILY_DRAWDOWN_LIMIT_PCT

# Crypto-specific daily drawdown limit (higher volatility tolerance).
CRYPTO_DAILY_DRAWDOWN_LIMIT_PCT = 3.0


def price_vs_ma_allowed(
    price: float,
    ma20: float,
    max_deviation_pct: float = 5.0,
) -> bool:
    """Anti-hallucination: allow only if price is within max_deviation_pct of 20-day MA."""
    if ma20 == 0:
        return False
    deviation_pct = abs(price - ma20) / ma20 * 100.0
    return deviation_pct <= max_deviation_pct


def compute_daily_drawdown(
    equity_at_open: float,
    current_equity: float,
) -> float:
    """Compute current daily drawdown percentage given starting and current equity."""
    if equity_at_open <= 0:
        return 0.0
    return max(0.0, (equity_at_open - current_equity) / equity_at_open * 100.0)


def should_trigger_circuit_breaker(drawdown_pct: float, asset_class: str = "EQUITY") -> bool:
    """Return True if drawdown_pct breaches or equals configured daily limit.

    Equity uses DAILY_DRAWDOWN_LIMIT_PCT (e.g. 1.5%); crypto uses a higher 3% limit.
    """
    ac = (asset_class or "EQUITY").upper()
    if ac == "CRYPTO":
        limit = float(CRYPTO_DAILY_DRAWDOWN_LIMIT_PCT)
    else:
        # Default for EQUITY and FOREX
        limit = float(DAILY_DRAWDOWN_LIMIT_PCT)
    return drawdown_pct >= limit


def build_failure_state(
    equity_at_open: float,
    current_equity: float,
    positions_snapshot: Dict,
    sentiment_snapshot: Dict | None = None,
    charts_snapshot: Dict | None = None,
    agent_summary: Dict | None = None,
) -> Dict:
    """Build a failure_state dict for write_post_mortem when circuit breaker fires."""
    drawdown_pct = compute_daily_drawdown(equity_at_open, current_equity)
    return {
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "equity_at_open": float(equity_at_open),
        "current_equity": float(current_equity),
        "drawdown_pct": float(drawdown_pct),
        "positions_snapshot": positions_snapshot or {},
        "sentiment_snapshot": sentiment_snapshot or {},
        "charts_snapshot": charts_snapshot or {},
        "agent_summary": agent_summary or {},
    }


def trailing_take_profit(
    entry_price: float,
    side: str,
    current_price: float,
    initial_stop: float,
    target_r_multiple: float = 2.0,
) -> Dict[str, float]:
    """Trailing take-profit helper using R-multiple framework.

    R-logic:
      - risk_per_unit = |entry_price - initial_stop|
      - target_price = entry_price +/- target_r_multiple * risk_per_unit
      - 50% target price = entry_price +/- 0.5 * target_r_multiple * risk_per_unit

    Rules:
      1) Initial: stop at initial_stop.
      2) Once price hits 50% of target: lock in break-even stop at entry_price.
      3) Once price hits full target: trail stop at 50% of remaining gain:
         - For longs: stop = entry_price + 0.5 * (current_price - entry_price)
         - For shorts: stop = entry_price - 0.5 * (entry_price - current_price)

    Returns dict with:
      {
        "initial_stop": float,
        "target_price": float,
        "half_target_price": float,
        "current_stop": float,
        "stage": 0 | 1 | 2,  # 0=initial, 1=breakeven, 2=trailing
      }
    """
    side_norm = (side or "").lower()
    if side_norm not in {"buy", "sell"}:
        raise ValueError("side must be 'buy' or 'sell'")

    risk_per_unit = abs(entry_price - initial_stop)
    if risk_per_unit <= 0:
        raise ValueError("initial_stop must be different from entry_price")

    r = float(target_r_multiple)
    if r <= 0:
        raise ValueError("target_r_multiple must be positive")

    if side_norm == "buy":
        target_price = entry_price + r * risk_per_unit
        half_target_price = entry_price + 0.5 * r * risk_per_unit
        # Stage 0: before half target
        if current_price < half_target_price:
            current_stop = initial_stop
            stage = 0
        # Stage 1: between half target and full target -> break-even stop
        elif current_price < target_price:
            current_stop = entry_price
            stage = 1
        else:
            # Stage 2: beyond target -> trail at 50% of current gain
            gain = max(0.0, current_price - entry_price)
            current_stop = entry_price + 0.5 * gain
            stage = 2
    else:
        # short
        target_price = entry_price - r * risk_per_unit
        half_target_price = entry_price - 0.5 * r * risk_per_unit
        # For shorts, prices moving DOWN are favorable
        if current_price > half_target_price:
            current_stop = initial_stop
            stage = 0
        elif current_price > target_price:
            current_stop = entry_price
            stage = 1
        else:
            gain = max(0.0, entry_price - current_price)
            current_stop = entry_price - 0.5 * gain
            stage = 2

    return {
        "initial_stop": float(initial_stop),
        "target_price": float(target_price),
        "half_target_price": float(half_target_price),
        "current_stop": float(current_stop),
        "stage": float(stage),
    }


