"""RegimeTest: 2022 Tech Bear Market, August 2024 Volatility Spike.

This module provides helpers to run stress tests over specific market regimes
using the existing backtesting engine and signal generator.

Regimes (auditable):
  1) 2022 Tech Bear Market: 2022-01-01 to 2022-12-31
  2) August 2024 Volatility Spike: 2024-08-01 to 2024-08-31

For each regime, we:
  - slice the OHLCV data to the given date range,
  - generate signals using the rule-based surrogate (or a provided signal_fn),
  - run a backtest,
  - compute:
      * total return
      * max drawdown
      * win rate
      * Sharpe
      * whether the path would have breached the daily DD circuit breaker.

The main entrypoint is `run_regime_tests(symbol, ohlcv_df, ...)` which returns a
list of RegimeTestResult records suitable for logging or reporting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import numpy as np
import pandas as pd

from dine_trade.backtesting.engine import BacktestResult, run_backtest
from dine_trade.backtesting.signal_from_agents import generate_signals
from dine_trade.config.settings import DAILY_DRAWDOWN_LIMIT_PCT


# Loosely-typed signal function: must accept (symbol, ohlcv_df, ...)
# and return list[dict] signals. We rely on keyword arguments for clarity.
SignalFn = Callable[..., List[dict]]


@dataclass
class RegimeTestResult:
    regime_name: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    total_return: float
    max_drawdown: float
    win_rate: float
    sharpe: float
    breached_dd_limit: bool


def _slice_regime(
    ohlcv_df: pd.DataFrame,
    start: str,
    end: str,
) -> pd.DataFrame:
    df = ohlcv_df.copy()
    if "date" not in df.columns or "close" not in df.columns:
        raise ValueError("ohlcv_df must contain 'date' and 'close' columns")
    df["date"] = pd.to_datetime(df["date"])
    mask = (df["date"] >= pd.to_datetime(start)) & (df["date"] <= pd.to_datetime(end))
    regime_df = df.loc[mask].sort_values("date").reset_index(drop=True)
    return regime_df


def _breaches_daily_dd_limit(equity_series: pd.Series, limit_pct: float) -> bool:
    """Return True if daily drawdown ever exceeds/equals limit_pct."""
    equity = equity_series.astype(float).values
    roll_max = np.maximum.accumulate(equity)
    valid = roll_max > 0
    dd = np.zeros_like(equity, dtype=float)
    dd[valid] = (roll_max[valid] - equity[valid]) / roll_max[valid] * 100.0
    return bool(np.any(dd >= limit_pct))


def _run_regime(
    symbol: str,
    regime_name: str,
    regime_df: pd.DataFrame,
    *,
    initial_equity: float,
    risk_per_trade_pct: float,
    slippage_bps: float,
    signal_fn: SignalFn,
    dd_limit_pct: float,
) -> Optional[RegimeTestResult]:
    if regime_df.empty:
        return None

    start_date = regime_df["date"].iloc[0]
    end_date = regime_df["date"].iloc[-1]

    signals = signal_fn(
        symbol,
        regime_df,
        initial_equity=initial_equity,
        risk_per_trade_pct=risk_per_trade_pct,
    )

    bt: BacktestResult = run_backtest(
        regime_df,
        signals,
        initial_equity=initial_equity,
        slippage_bps=slippage_bps,
    )

    breached = _breaches_daily_dd_limit(bt.equity_curve, dd_limit_pct)

    return RegimeTestResult(
        regime_name=regime_name,
        start_date=start_date,
        end_date=end_date,
        total_return=bt.total_return,
        max_drawdown=bt.max_drawdown,
        win_rate=bt.win_rate,
        sharpe=bt.sharpe,
        breached_dd_limit=breached,
    )


def run_regime_tests(
    symbol: str,
    ohlcv_df: pd.DataFrame,
    *,
    initial_equity: float = 100_000.0,
    risk_per_trade_pct: float = 1.0,
    slippage_bps: float = 1.0,
    signal_fn: SignalFn | None = None,
    dd_limit_pct: Optional[float] = None,
) -> List[RegimeTestResult]:
    """Run mandatory regime tests for audit.

    Regimes:
      1) "2022 Tech Bear Market"  : 2022-01-01 to 2022-12-31
      2) "Aug 2024 Volatility"    : 2024-08-01 to 2024-08-31

    Returns:
      List of RegimeTestResult; some entries may be missing if data is not
      available for a regime (e.g. future dates).
    """
    if signal_fn is None:
        signal_fn = generate_signals
    if dd_limit_pct is None:
        dd_limit_pct = float(DAILY_DRAWDOWN_LIMIT_PCT)

    df = ohlcv_df.copy()
    if "date" not in df.columns or "close" not in df.columns:
        raise ValueError("ohlcv_df must contain 'date' and 'close' columns")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    regimes = [
        ("2022 Tech Bear Market", "2022-01-01", "2022-12-31"),
        ("Aug 2024 Volatility Spike", "2024-08-01", "2024-08-31"),
    ]

    results: List[RegimeTestResult] = []

    for name, start, end in regimes:
        regime_df = _slice_regime(df, start, end)
        res = _run_regime(
            symbol,
            name,
            regime_df,
            initial_equity=initial_equity,
            risk_per_trade_pct=risk_per_trade_pct,
            slippage_bps=slippage_bps,
            signal_fn=signal_fn,
            dd_limit_pct=dd_limit_pct,
        )
        if res is not None:
            results.append(res)

    return results

