"""Global kill-switch and circuit breaker helpers.

- Kill-switch: env var or file flag TRADING_ENABLED=false disables all order submission.
- Circuit breaker: daily drawdown >= configured limit (e.g. 1.5%) must also prevent new trades.
"""

from __future__ import annotations

import os
from typing import Optional

from dine_trade.config.settings import DAILY_DRAWDOWN_LIMIT_PCT, TRADING_ENABLED


def trading_enabled(flag_file: Optional[str] = None) -> bool:
    """Return True if trading is allowed.

    Order of precedence:
      1) File flag (if provided): if file exists and contains 'false' (case-insensitive),
         trading is disabled.
      2) Env-backed config TRADING_ENABLED from settings.
    """
    # File flag override (e.g. ./TRADING_ENABLED)
    path = flag_file or os.getenv("TRADING_ENABLED_FILE") or "TRADING_ENABLED"
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                val = f.read().strip().lower()
            if val in {"false", "0", "no", "off"}:
                return False
    except OSError:
        # If file can't be read, ignore and fall back to env/config
        pass

    # Fallback: env-backed setting
    return bool(TRADING_ENABLED)


def circuit_breaker_tripped(daily_drawdown_pct: float) -> bool:
    """Return True if daily drawdown breaches or equals configured limit.

    This mirrors should_trigger_circuit_breaker in risk.limits but is provided here
    for the Executor/strategy layer to make a single 'can trade?' decision.
    """
    try:
        dd = float(daily_drawdown_pct)
    except (TypeError, ValueError):
        dd = 0.0
    return dd >= float(DAILY_DRAWDOWN_LIMIT_PCT)


def can_submit_orders(daily_drawdown_pct: Optional[float] = None, flag_file: Optional[str] = None) -> bool:
    """Single gate used by Executor before any order submission.

    Returns False if:
      - Global kill-switch is off (TRADING_ENABLED=false via env or file), or
      - Circuit breaker is tripped (daily_drawdown_pct >= DAILY_DRAWDOWN_LIMIT_PCT).
    """
    if not trading_enabled(flag_file=flag_file):
        return False
    if daily_drawdown_pct is not None and circuit_breaker_tripped(daily_drawdown_pct):
        return False
    return True

