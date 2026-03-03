"""Risk Officer agent.

Inputs:
  - symbol: ticker string
  - price: current instrument price
  - account_equity: current account equity in dollars
  - position_size_usd: optional current/desired notional exposure in dollars
  - qty: optional current/desired quantity (shares)
  - volatility: optional volatility proxy (e.g. ATR)
  - daily_drawdown_pct: optional current daily drawdown percentage

Output:
  {
    "verdict": "APPROVE" | "REJECT",
    "max_qty": float,
    "reasoning": str
  }
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from dine_trade.config.settings import (
    DAILY_DRAWDOWN_LIMIT_PCT,
    MAX_RISK_PER_TRADE_PCT,
)
from dine_trade.risk.kelly import kelly_fraction, position_size_cap


@dataclass
class RiskInputs:
    symbol: str
    price: float
    account_equity: float
    position_size_usd: Optional[float] = None
    qty: Optional[float] = None
    volatility: Optional[float] = None
    daily_drawdown_pct: Optional[float] = None
    # Optional Kelly inputs (e.g. from backtests)
    win_rate: Optional[float] = None
    avg_win: Optional[float] = None
    avg_loss: Optional[float] = None


def _max_qty_from_cap(notional_cap: float, price: float) -> float:
    if price <= 0 or notional_cap <= 0:
        return 0.0
    return max(0.0, notional_cap / price)


def evaluate_risk(inputs: RiskInputs) -> Dict[str, object]:
    """Core risk evaluation logic used by the Risk Officer agent."""
    symbol = inputs.symbol
    price = float(inputs.price)
    equity = float(inputs.account_equity)

    if price <= 0 or equity <= 0:
        return {
            "verdict": "REJECT",
            "max_qty": 0.0,
            "reasoning": "Invalid price or account equity.",
        }

    # 1) Daily drawdown circuit breaker
    dd_limit = float(DAILY_DRAWDOWN_LIMIT_PCT)
    if inputs.daily_drawdown_pct is not None:
        if inputs.daily_drawdown_pct >= dd_limit:
            return {
                "verdict": "REJECT",
                "max_qty": 0.0,
                "reasoning": f"Daily drawdown {inputs.daily_drawdown_pct:.2f}% >= limit {dd_limit:.2f}%.",
            }

    # 2) Kelly-based cap (fractional Kelly) on notional exposure
    kelly_f = 0.0
    if (
        inputs.win_rate is not None
        and inputs.avg_win is not None
        and inputs.avg_loss is not None
    ):
        kelly_f = kelly_fraction(
            win_rate=inputs.win_rate,
            avg_win=inputs.avg_win,
            avg_loss=inputs.avg_loss,
        )

    notional_cap = position_size_cap(
        equity=equity,
        risk_pct=float(MAX_RISK_PER_TRADE_PCT),
        volatility=inputs.volatility,
        kelly_f=kelly_f,
        kelly_fraction_cap=0.5,  # half-Kelly by default
    )
    max_qty_cap = _max_qty_from_cap(notional_cap, price)

    # 3) Check proposed size (if any) against cap
    proposed_notional = None
    if inputs.position_size_usd is not None:
        proposed_notional = float(inputs.position_size_usd)
    elif inputs.qty is not None:
        proposed_notional = float(inputs.qty) * price

    if proposed_notional is not None and proposed_notional > 0:
        if proposed_notional > notional_cap:
            return {
                "verdict": "REJECT",
                "max_qty": float(max_qty_cap),
                "reasoning": (
                    f"Proposed position ${proposed_notional:,.2f} exceeds risk cap "
                    f"${notional_cap:,.2f} (max_qty ~ {max_qty_cap:.4f} at price {price})."
                ),
            }

    reasoning_parts = []
    reasoning_parts.append(
        f"Max risk per trade {MAX_RISK_PER_TRADE_PCT:.2f}% of equity -> cap ${notional_cap:,.2f}."
    )
    if kelly_f > 0:
        reasoning_parts.append(f"Kelly fraction {kelly_f:.3f} (half-Kelly applied).")
    if inputs.volatility is not None:
        reasoning_parts.append(f"Volatility adjustment applied (vol={inputs.volatility}).")
    if inputs.daily_drawdown_pct is not None:
        reasoning_parts.append(
            f"Current daily drawdown {inputs.daily_drawdown_pct:.2f}% < limit {dd_limit:.2f}%."
        )

    return {
        "verdict": "APPROVE",
        "max_qty": float(max_qty_cap),
        "reasoning": " ".join(reasoning_parts),
    }


def run_risk_officer(
    symbol: str,
    price: float,
    account_equity: float,
    position_size_usd: Optional[float] = None,
    qty: Optional[float] = None,
    volatility: Optional[float] = None,
    daily_drawdown_pct: Optional[float] = None,
    win_rate: Optional[float] = None,
    avg_win: Optional[float] = None,
    avg_loss: Optional[float] = None,
) -> Dict[str, object]:
    """Convenience wrapper for the Risk Officer agent.

    The orchestration layer can call this with symbol, price, and equity,
    plus any optional sizing and Kelly parameters.
    """
    inputs = RiskInputs(
        symbol=symbol,
        price=price,
        account_equity=account_equity,
        position_size_usd=position_size_usd,
        qty=qty,
        volatility=volatility,
        daily_drawdown_pct=daily_drawdown_pct,
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
    )
    return evaluate_risk(inputs)

