"""Walk-forward optimization utilities for DineTrade.

Implements a simple rolling-window walk-forward backtest:

- Split historical OHLCV into contiguous train/test windows.
- For each window:
    * Use the train window to fit/configure a strategy (for now, this module
      delegates to a provided `signal_fn` and does not optimize hyperparams).
    * Generate signals on the **test** window only.
    * Run `run_backtest` on the test window to obtain out-of-sample metrics.

This avoids evaluating a strategy only on in-sample data and helps reduce
curve fitting.

Public API:

    from dine_trade.backtesting.walk_forward import walk_forward_test
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Sequence

import pandas as pd

from dine_trade.backtesting.engine import BacktestResult, run_backtest
from dine_trade.backtesting.signal_from_agents import generate_signals


# Loosely-typed signal function: must accept (symbol, ohlcv_df, ...)
# and return list[dict] signals. We rely on keyword arguments for clarity.
SignalFn = Callable[..., List[dict]]


@dataclass
class WalkForwardWindowResult:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    result: BacktestResult


@dataclass
class WalkForwardSummary:
    windows: List[WalkForwardWindowResult]
    avg_return: float
    avg_max_drawdown: float
    avg_sharpe: float


def _window_slices(
    df: pd.DataFrame,
    train_size: int,
    test_size: int,
) -> Sequence[tuple[slice, slice]]:
    """Yield (train_slice, test_slice) index slices for rolling windows."""
    n = len(df)
    if n < train_size + test_size:
        return []

    slices: List[tuple[slice, slice]] = []
    start = 0
    while True:
        train_start = start
        train_end = train_start + train_size
        test_start = train_end
        test_end = test_start + test_size
        if test_end > n:
            break
        slices.append((slice(train_start, train_end), slice(test_start, test_end)))
        start += test_size  # roll forward by one test window
    return slices


def walk_forward_test(
    symbol: str,
    ohlcv_df: pd.DataFrame,
    *,
    train_size: int = 252,
    test_size: int = 63,
    initial_equity: float = 100_000.0,
    risk_per_trade_pct: float = 1.0,
    slippage_bps: float = 1.0,
    signal_fn: SignalFn | None = None,
) -> WalkForwardSummary:
    """Run walk-forward tests across historical data.

    Parameters:
      - symbol: asset symbol (e.g. "NVDA").
      - ohlcv_df: full OHLCV DataFrame with 'date' and 'close'.
      - train_size: number of bars in each training window (e.g. 252 trading days).
      - test_size: number of bars in each test window (e.g. 63 trading days).
      - initial_equity: starting equity for each window's backtest.
      - risk_per_trade_pct: passed to signal_fn, controls position sizing.
      - slippage_bps: slippage per trade for the backtest engine.
      - signal_fn: function (symbol, df_window, initial_equity, risk_pct) -> list[dict].
        Defaults to backtesting.signal_from_agents.generate_signals.

    Returns:
      WalkForwardSummary with per-window BacktestResult and averages.

    Note: For now, the train window is not used to fit hyperparameters. It
    exists to match standard walk-forward methodology and can be used in the
    future for optimizer-based strategies.
    """
    if signal_fn is None:
        signal_fn = generate_signals

    df = ohlcv_df.copy()
    if "date" not in df.columns or "close" not in df.columns:
        raise ValueError("ohlcv_df must contain 'date' and 'close' columns")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    windows: List[WalkForwardWindowResult] = []

    for train_slice, test_slice in _window_slices(df, train_size, test_size):
        train_df = df.iloc[train_slice].reset_index(drop=True)
        test_df = df.iloc[test_slice].reset_index(drop=True)

        if train_df.empty or test_df.empty:
            continue

        train_start = train_df["date"].iloc[0]
        train_end = train_df["date"].iloc[-1]
        test_start = test_df["date"].iloc[0]
        test_end = test_df["date"].iloc[-1]

        # Generate signals on the TEST window only using the chosen signal function.
        signals = signal_fn(
            symbol,
            test_df,
            initial_equity=initial_equity,
            risk_per_trade_pct=risk_per_trade_pct,
        )

        if not signals:
            # No trades in this test window; still produce a flat equity curve.
            result = run_backtest(
                test_df,
                [],
                initial_equity=initial_equity,
                slippage_bps=slippage_bps,
            )
        else:
            result = run_backtest(
                test_df,
                signals,
                initial_equity=initial_equity,
                slippage_bps=slippage_bps,
            )

        windows.append(
            WalkForwardWindowResult(
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                result=result,
            )
        )

    if not windows:
        return WalkForwardSummary(windows=[], avg_return=0.0, avg_max_drawdown=0.0, avg_sharpe=0.0)

    returns = [w.result.total_return for w in windows]
    max_dds = [w.result.max_drawdown for w in windows]
    sharpes = [w.result.sharpe for w in windows]

    avg_return = float(sum(returns) / len(returns)) if returns else 0.0
    avg_max_dd = float(sum(max_dds) / len(max_dds)) if max_dds else 0.0
    avg_sharpe = float(sum(sharpes) / len(sharpes)) if sharpes else 0.0

    return WalkForwardSummary(
        windows=windows,
        avg_return=avg_return,
        avg_max_drawdown=avg_max_dd,
        avg_sharpe=avg_sharpe,
    )

