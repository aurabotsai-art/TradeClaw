"""Backtesting engine for DineTrade.

Implements a simple vectorized backtest:

Inputs:
  - ohlcv_df: pandas.DataFrame with at least columns:
      "date" (datetime-like or string) and "close" (numeric).
  - signals: list of dicts, each with:
      {
        "date": datetime/date/str (signal date, must align with ohlcv_df["date"]),
        "symbol": str,
        "side": "buy" or "sell",
        "qty": float      # position size in units (shares, contracts, etc.)
                          # OR 'notional' key for $-based size, not both.
      }

Assumptions:
  - Single-symbol backtest (symbol field is informational).
  - Orders are filled at the **close** of the signal bar.
  - No overlapping positions: this engine treats each signal as a complete
    round-trip trade: enter on next signal of opposite side OR close on
    exit signal (extension possible later).
  - Simple per-trade PnL: (exit_price - entry_price) * signed_qty minus
    a slippage cost of `slippage_bps` basis points per trade.

Output:
  - BacktestResult dataclass with:
      equity_curve: pd.Series indexed by date
      total_return: float (percentage)
      max_drawdown: float (percentage)
      win_rate: float (0..1)
      sharpe: float (annualized, using daily returns)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    total_return: float
    max_drawdown: float
    win_rate: float
    sharpe: float


def _normalize_ohlcv_df(ohlcv_df: pd.DataFrame) -> pd.DataFrame:
    df = ohlcv_df.copy()
    if "date" not in df.columns:
        raise ValueError("ohlcv_df must have a 'date' column")
    if "close" not in df.columns:
        raise ValueError("ohlcv_df must have a 'close' column")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def _signals_to_series(
    signals: Iterable[dict],
    df: pd.DataFrame,
) -> pd.Series:
    """Map list of signal dicts to a pandas Series of signed quantities by date.

    For now we assume:
      - 'side' is 'buy' or 'sell'
      - 'qty' is the number of units to trade
      - multiple signals on the same date are summed.
    """
    if not signals:
        return pd.Series(0.0, index=df["date"])

    sig_df = pd.DataFrame(signals)
    if sig_df.empty:
        return pd.Series(0.0, index=df["date"])

    if "date" not in sig_df.columns or "side" not in sig_df.columns:
        raise ValueError("each signal must have 'date' and 'side' keys")
    if "qty" not in sig_df.columns:
        raise ValueError("each signal must have 'qty' key (units)")

    sig_df["date"] = pd.to_datetime(sig_df["date"])
    side_sign = sig_df["side"].str.lower().map({"buy": 1.0, "sell": -1.0})
    if side_sign.isnull().any():
        raise ValueError("signal 'side' must be 'buy' or 'sell'")
    sig_df["signed_qty"] = side_sign * sig_df["qty"].astype(float)

    grouped = sig_df.groupby("date")["signed_qty"].sum()
    # Align with OHLCV dates; fill missing with 0.
    signed_qty_series = grouped.reindex(df["date"]).fillna(0.0)
    signed_qty_series.index = df["date"]
    return signed_qty_series


def run_backtest(
    ohlcv_df: pd.DataFrame,
    signals: List[dict],
    *,
    initial_equity: float = 100_000.0,
    slippage_bps: float = 1.0,  # 1 basis point = 0.01%; default 0.01% per trade
) -> BacktestResult:
    """Run a simple vectorized backtest with fills at close and slippage.

    This engine assumes all trades are closed by the end of the data (no open
    position at the last bar). Complex multi-position / overlapping logic can be
    layered on top later as needed.
    """
    if initial_equity <= 0:
        raise ValueError("initial_equity must be positive")

    df = _normalize_ohlcv_df(ohlcv_df)
    prices = df["close"].astype(float).values
    dates = df["date"]

    # Signed quantities per date (positive = buy, negative = sell)
    signed_qty = _signals_to_series(signals, df).values

    # Position: cumulative sum of signed quantities
    position = np.cumsum(signed_qty)

    # Daily PnL from price changes on held position
    price_diff = np.diff(prices, prepend=prices[0])
    pnl_price = position * price_diff

    # Slippage cost per trade: slippage_bps/10000 * |qty| * price
    slippage_rate = slippage_bps / 10_000.0
    slippage_cost = np.abs(signed_qty) * prices * slippage_rate * -1.0

    daily_pnl = pnl_price + slippage_cost

    equity = initial_equity + np.cumsum(daily_pnl)
    equity_series = pd.Series(equity, index=dates)

    # Total return
    total_return = (equity_series.iloc[-1] / initial_equity - 1.0) * 100.0

    # Max drawdown (percentage)
    roll_max = equity_series.cummax()
    drawdown = (equity_series - roll_max) / roll_max
    max_drawdown = drawdown.min() * 100.0 if len(drawdown) > 0 else 0.0

    # Per-trade metrics (win rate)
    trade_indices = np.where(signed_qty != 0.0)[0]
    trade_pnls: List[float] = []
    for idx in trade_indices:
        trade_pnls.append(daily_pnl[idx])
    wins = [p for p in trade_pnls if p > 0]
    win_rate = (len(wins) / len(trade_pnls)) if trade_pnls else 0.0

    # Daily returns for Sharpe
    returns = equity_series.pct_change().dropna()
    if len(returns) > 1 and returns.std() > 0:
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252.0)
    else:
        sharpe = 0.0

    return BacktestResult(
        equity_curve=equity_series,
        total_return=float(total_return),
        max_drawdown=float(max_drawdown),
        win_rate=float(win_rate),
        sharpe=float(sharpe),
    )

