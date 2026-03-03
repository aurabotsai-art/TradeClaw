"""Signal generation for backtests from agent/consensus logic.

This module provides two approaches:

1) Rule-based surrogate (`generate_signals_rule_based`) that approximates the
   live consensus logic using technical indicators only. This is *fast* and
   does not call Gemini, so it is suitable for large backtests.

2) A scaffold for a future full consensus-based generator that would call
   `orchestration.run_consensus` for each date. This is intentionally left
   commented/not wired by default because Gemini calls are expensive.

The public helper `generate_signals` currently uses the rule-based surrogate.
It returns a list of signal dicts ready for the backtesting engine:

    {
      "date": <datetime>,
      "symbol": <str>,
      "side": "buy" or "sell",
      "qty": <float>,  # units (shares) sized as % of equity
    }
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd


@dataclass
class Signal:
    date: pd.Timestamp
    symbol: str
    side: str  # 'buy' or 'sell'
    qty: float


def _compute_indicators(ohlcv_df: pd.DataFrame) -> pd.DataFrame:
    """Compute basic indicators over the entire OHLCV history.

    Indicators:
      - ma20, ma50 (simple moving averages)
      - rsi14
    """
    df = ohlcv_df.copy()
    if "date" not in df.columns or "close" not in df.columns:
        raise ValueError("ohlcv_df must contain 'date' and 'close' columns")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    close = df["close"].astype(float)

    # Moving averages
    df["ma20"] = close.rolling(window=20, min_periods=5).mean()
    df["ma50"] = close.rolling(window=50, min_periods=10).mean()

    # RSI(14)
    delta = close.diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(gain).rolling(window=14, min_periods=5).mean()
    roll_down = pd.Series(loss).rolling(window=14, min_periods=5).mean()
    rs = roll_up / (roll_down.replace(0, np.nan))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    df["rsi14"] = rsi

    return df


def generate_signals_rule_based(
    symbol: str,
    ohlcv_df: pd.DataFrame,
    *,
    initial_equity: float = 100_000.0,
    risk_per_trade_pct: float = 1.0,
) -> List[dict]:
    """Generate naive long/flat signals using technical rules.

    This is a *surrogate* for the full multi-agent consensus:
      - Long bias when ma20 > ma50 and RSI above 50 (uptrend with strength).
      - Exit/flat when ma20 < ma50 or RSI below 40 (downtrend/weakness).

    Position sizing:
      - target_notional = equity * risk_per_trade_pct / 100
      - qty = target_notional / close

    Returns:
      list of dicts: {"date", "symbol", "side", "qty}
    """
    if initial_equity <= 0:
        raise ValueError("initial_equity must be positive")
    if risk_per_trade_pct <= 0:
        raise ValueError("risk_per_trade_pct must be positive")

    df = _compute_indicators(ohlcv_df)
    target_notional = initial_equity * (risk_per_trade_pct / 100.0)

    signals: List[Signal] = []
    in_position = False
    last_qty = 0.0

    for idx, row in df.iterrows():
        ma20 = row.get("ma20")
        ma50 = row.get("ma50")
        rsi = row.get("rsi14")
        close = float(row["close"])
        dt = pd.to_datetime(row["date"])

        # Skip early rows where indicators are not formed
        if pd.isna(ma20) or pd.isna(ma50) or pd.isna(rsi):
            continue

        uptrend = ma20 > ma50
        downtrend = ma20 < ma50
        strong = rsi > 50
        weak = rsi < 40

        # Long entry condition: uptrend + strength, not already in position
        if not in_position and uptrend and strong:
            qty = max(0.0, target_notional / close)
            if qty > 0:
                signals.append(Signal(date=dt, symbol=symbol, side="buy", qty=qty))
                in_position = True
                last_qty = qty
            continue

        # Exit condition: downtrend or clear weakness while in position
        if in_position and (downtrend or weak):
            if last_qty > 0:
                signals.append(Signal(date=dt, symbol=symbol, side="sell", qty=last_qty))
            in_position = False
            last_qty = 0.0

    # Convert to list[dict] for the backtest engine
    return [
        {"date": s.date, "symbol": s.symbol, "side": s.side, "qty": s.qty}
        for s in signals
    ]


def generate_signals(
    symbol: str,
    ohlcv_df: pd.DataFrame,
    *,
    initial_equity: float = 100_000.0,
    risk_per_trade_pct: float = 1.0,
) -> List[dict]:
    """Public helper for signal generation.

    Currently delegates to `generate_signals_rule_based`, which is fast and does
    not call Gemini. In the future, this can be swapped to a full consensus-
    based implementation or accept a strategy parameter to choose which
    generator to use.
    """
    return generate_signals_rule_based(
        symbol=symbol,
        ohlcv_df=ohlcv_df,
        initial_equity=initial_equity,
        risk_per_trade_pct=risk_per_trade_pct,
    )

