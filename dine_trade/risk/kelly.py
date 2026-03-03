"""Kelly-based position sizing utilities.

The Risk Officer agent uses these helpers to cap position size based on
estimated edge and volatility, in addition to hard max-risk constraints.
"""

from __future__ import annotations

from typing import Optional


def kelly_fraction(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
) -> float:
    """Compute Kelly fraction given win rate and average win/loss (absolute values).

    Kelly f* = p - (q / R)
      where p = win_rate, q = 1 - p, R = avg_win / avg_loss

    Returns 0.0 when inputs are invalid or imply negative edge.
    """
    if not 0 < win_rate < 1:
        return 0.0
    if avg_win <= 0 or avg_loss <= 0:
        return 0.0
    p = float(win_rate)
    q = 1.0 - p
    r = avg_win / avg_loss
    if r <= 0:
        return 0.0
    f_star = p - (q / r)
    return max(0.0, float(f_star))


def position_size_cap(
    equity: float,
    risk_pct: float,
    volatility: Optional[float] = None,
    kelly_f: float = 0.0,
    kelly_fraction_cap: float = 0.5,
) -> float:
    """Maximum notional exposure for a single position.

    - equity: account equity in dollars.
    - risk_pct: hard cap on % of equity you are willing to lose on this trade
      (e.g. config MAX_RISK_PER_TRADE_PCT).
    - volatility: optional measure (e.g. ATR). If provided, higher volatility
      reduces size by 1 / (1 + vol).
    - kelly_f: Kelly fraction estimate (0..1). We apply a fractional Kelly cap.
    - kelly_fraction_cap: cap Kelly at this fraction (e.g. 0.5 = half Kelly).

    Returns a dollar notional cap. The Risk Officer converts that to quantity
    by dividing by instrument price.
    """
    if equity <= 0 or risk_pct <= 0:
        return 0.0

    # Hard risk budget: maximum dollars we are prepared to put at risk
    risk_budget = equity * (risk_pct / 100.0)

    # Kelly scaling (fractional Kelly, default half-Kelly)
    effective_kelly = min(max(kelly_f, 0.0), 1.0) * float(kelly_fraction_cap)
    if effective_kelly <= 0:
        # If no edge estimate, fall back to pure risk-budget based cap
        base_cap = risk_budget
    else:
        base_cap = equity * effective_kelly
        # Do not exceed hard risk budget
        base_cap = min(base_cap, risk_budget)

    # Volatility adjustment: reduce size when volatility is high
    if volatility is not None and volatility > 0:
        base_cap = base_cap / (1.0 + float(volatility))

    return max(0.0, base_cap)

