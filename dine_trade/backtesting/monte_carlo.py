"""Monte Carlo analysis for DineTrade backtests.

This module takes a historical equity curve (or, equivalently, its daily
returns), bootstraps many alternative return paths, and computes the
distribution of path-dependent risk metrics such as max drawdown and the
probability of breaching a daily drawdown limit.

Usage example:

    from dine_trade.backtesting.engine import run_backtest
    from dine_trade.backtesting.monte_carlo import monte_carlo_from_equity

    result = run_backtest(ohlcv_df, signals, initial_equity=100_000)
    mc = monte_carlo_from_equity(result.equity_curve, n_paths=1000)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

from dine_trade.config.settings import DAILY_DRAWDOWN_LIMIT_PCT


@dataclass
class MonteCarloSummary:
    """Aggregate Monte Carlo stats over many bootstrap paths."""

    n_paths: int
    dd_limit_pct: float
    max_drawdowns: List[float]          # list of max DD (%) per path
    failure_rate: float                 # fraction of paths breaching dd_limit_pct
    mean_max_drawdown: float
    p05_max_drawdown: float             # 5th percentile (more optimistic)
    p50_max_drawdown: float             # median
    p95_max_drawdown: float             # 95th percentile (worst tail)


def _max_drawdown_pct(equity: np.ndarray) -> float:
    """Compute max drawdown in percent for a 1D equity array."""
    roll_max = np.maximum.accumulate(equity)
    # Avoid division by zero
    valid = roll_max > 0
    drawdowns = np.zeros_like(equity, dtype=float)
    drawdowns[valid] = (equity[valid] - roll_max[valid]) / roll_max[valid]
    return float(drawdowns.min() * 100.0)


def _breaches_limit(equity: np.ndarray, limit_pct: float) -> bool:
    """Return True if daily drawdown ever exceeds/equals limit_pct."""
    roll_max = np.maximum.accumulate(equity)
    valid = roll_max > 0
    dd = np.zeros_like(equity, dtype=float)
    dd[valid] = (roll_max[valid] - equity[valid]) / roll_max[valid] * 100.0
    return bool(np.any(dd >= limit_pct))


def monte_carlo_from_equity(
    equity_curve: pd.Series,
    *,
    n_paths: int = 1000,
    dd_limit_pct: Optional[float] = None,
    seed: Optional[int] = None,
) -> MonteCarloSummary:
    """Run Monte Carlo bootstrap on an equity curve.

    Parameters:
      - equity_curve: pd.Series of equity values indexed by date.
      - n_paths: number of bootstrap paths to simulate (e.g., 1000).
      - dd_limit_pct: daily drawdown limit; defaults to config DAILY_DRAWDOWN_LIMIT_PCT.
      - seed: optional random seed for reproducibility.

    Returns:
      MonteCarloSummary with distribution of max drawdowns and failure rate.
    """
    if dd_limit_pct is None:
        dd_limit_pct = float(DAILY_DRAWDOWN_LIMIT_PCT)

    if len(equity_curve) < 2:
        raise ValueError("Equity curve must have at least 2 points for Monte Carlo.")

    equity = equity_curve.astype(float).values
    initial_equity = equity[0]

    # Compute daily returns
    # r_t = equity_t / equity_{t-1} - 1
    returns = pd.Series(equity).pct_change().dropna().values
    if returns.size == 0:
        raise ValueError("Equity curve returns are all zero or invalid for Monte Carlo.")

    rng = np.random.default_rng(seed)

    max_drawdowns: List[float] = []
    failures = 0

    n = len(returns)
    for _ in range(n_paths):
        # Bootstrap returns with replacement
        sampled = rng.choice(returns, size=n, replace=True)
        # Reconstruct an equity path from returns
        eq_path = initial_equity * np.cumprod(1.0 + sampled)

        md = _max_drawdown_pct(eq_path)
        max_drawdowns.append(md)

        if _breaches_limit(eq_path, dd_limit_pct):
            failures += 1

    max_drawdowns_arr = np.array(max_drawdowns)
    mean_md = float(max_drawdowns_arr.mean())
    p05 = float(np.percentile(max_drawdowns_arr, 5))
    p50 = float(np.percentile(max_drawdowns_arr, 50))
    p95 = float(np.percentile(max_drawdowns_arr, 95))

    failure_rate = failures / n_paths if n_paths > 0 else 0.0

    return MonteCarloSummary(
        n_paths=n_paths,
        dd_limit_pct=float(dd_limit_pct),
        max_drawdowns=max_drawdowns,
        failure_rate=float(failure_rate),
        mean_max_drawdown=mean_md,
        p05_max_drawdown=p05,
        p50_max_drawdown=p50,
        p95_max_drawdown=p95,
    )

