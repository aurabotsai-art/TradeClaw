from __future__ import annotations

from typing import Literal

import pandas as pd

Side = Literal["long", "short"]


def compute_atr(ohlcv_df: pd.DataFrame, period: int = 14) -> float:
    """
    Compute Average True Range (ATR) over the last `period` bars.

    Expects `ohlcv_df` to have columns: ["high", "low", "close"] and be
    sorted in ascending time order.
    """
    if ohlcv_df is None or getattr(ohlcv_df, "empty", True):
        return 0.0

    period = max(1, int(period))
    df = ohlcv_df.copy()

    if not {"high", "low", "close"}.issubset(df.columns):
        return 0.0

    prev_close = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_series = tr.rolling(window=period, min_periods=period).mean()

    atr = atr_series.iloc[-1]
    try:
        return float(atr)
    except (TypeError, ValueError):
        return 0.0


def dynamic_stop_price(
    entry_price: float,
    side: Side,
    atr: float,
    multiplier: float = 2.0,
) -> float:
    """
    Compute initial ATR-based stop price.

    Long:  entry_price - (atr * multiplier)
    Short: entry_price + (atr * multiplier)
    """
    side_norm = str(side).lower()
    m = float(multiplier)
    a = float(atr)
    e = float(entry_price)

    if side_norm == "long":
        return e - a * m
    if side_norm == "short":
        return e + a * m
    raise ValueError("side must be 'long' or 'short'")


def trailing_stop(
    current_price: float,
    side: Side,
    atr: float,
    best_price: float,
    multiplier: float = 2.0,
) -> float:
    """
    Compute trailing ATR stop given current/best price.

    - best_price: most favorable price since entry
      * Long:   highest price seen
      * Short:  lowest price seen
    - Stop trails best_price by atr * multiplier:
      * Long:  stop = best_price - atr * multiplier
      * Short: stop = best_price + atr * multiplier

    The caller is responsible for updating best_price on each new tick:
      * Long:  best_price = max(best_price, current_price)
      * Short: best_price = min(best_price, current_price)
    """
    side_norm = str(side).lower()
    m = float(multiplier)
    a = float(atr)
    bp = float(best_price)

    if side_norm == "long":
        return bp - a * m
    if side_norm == "short":
        return bp + a * m
    raise ValueError("side must be 'long' or 'short'")


def stop_hit(current_price: float, side: Side, stop_price: float) -> bool:
    """
    Helper to check if stop has been hit/crossed.

    - Long:  stop is hit when current_price <= stop_price
    - Short: stop is hit when current_price >= stop_price
    """
    cp = float(current_price)
    sp = float(stop_price)
    side_norm = str(side).lower()

    if side_norm == "long":
        return cp <= sp
    if side_norm == "short":
        return cp >= sp
    raise ValueError("side must be 'long' or 'short'")

