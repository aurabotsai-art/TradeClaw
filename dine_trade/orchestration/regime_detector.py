from __future__ import annotations

"""
Market regime classifier.

classify_regime(ohlcv_df) -> str

Regimes:
    - "TRENDING_UP"
    - "TRENDING_DOWN"
    - "RANGING"
    - "HIGH_VOLATILITY"
    - "UNKNOWN"

Heuristics:
    - ADX > 25 AND price above 50MA  -> TRENDING_UP
    - ADX > 25 AND price below 50MA  -> TRENDING_DOWN
    - ADX < 20 AND price within Bollinger Bands -> RANGING
    - VIX-equivalent > 30 (approx. from realized volatility) -> HIGH_VOLATILITY

Redis caching helpers (15-minute regime cache) are provided for callers that
run regime detection on a schedule.
"""

from math import sqrt
from typing import Optional

import pandas as pd

from dine_trade.storage.redis_client import _get_client as _get_redis_client


def _compute_adx(ohlcv_df: pd.DataFrame, period: int = 14) -> float:
    """Compute a simple ADX approximation over the last `period` bars."""
    if ohlcv_df is None or getattr(ohlcv_df, "empty", True):
        return 0.0

    required_cols = {"high", "low", "close"}
    if not required_cols.issubset(ohlcv_df.columns):
        return 0.0

    df = ohlcv_df.copy()
    high = df["high"]
    low = df["low"]
    close = df["close"]

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move

    period = max(1, int(period))

    atr = tr.rolling(window=period, min_periods=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period, min_periods=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period, min_periods=period).mean() / atr)

    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).abs() * 100
    adx_series = dx.rolling(window=period, min_periods=period).mean()

    adx = adx_series.iloc[-1]
    try:
        return float(adx)
    except (TypeError, ValueError):
        return 0.0


def _compute_vix_equivalent(ohlcv_df: pd.DataFrame, lookback: int = 20) -> float:
    """
    Approximate a VIX-like volatility measure from returns.

    We compute log returns over the last `lookback` bars, take the standard
    deviation, and annualize:

        vol_annualized = std(log_returns) * sqrt(252)

    Then we express it in percent as VIX-equivalent.
    """
    if ohlcv_df is None or getattr(ohlcv_df, "empty", True):
        return 0.0
    if "close" not in ohlcv_df.columns:
        return 0.0

    closes = ohlcv_df["close"].astype(float)
    if closes.size < 2:
        return 0.0

    log_returns = (closes / closes.shift(1)).apply(lambda x: 0.0 if x <= 0 else pd.np.log(x))  # type: ignore[attr-defined]
    recent = log_returns.dropna().tail(lookback)
    if recent.empty:
        return 0.0

    std = recent.std()
    vol_annualized = std * sqrt(252.0)
    return float(vol_annualized * 100.0)


def classify_regime(ohlcv_df: pd.DataFrame) -> str:
    """
    Classify market regime based on OHLCV.

    Returns one of:
        "TRENDING_UP", "TRENDING_DOWN", "RANGING", "HIGH_VOLATILITY", "UNKNOWN".
    """
    if ohlcv_df is None or getattr(ohlcv_df, "empty", True):
        return "UNKNOWN"

    df = ohlcv_df.copy()
    if "close" not in df.columns:
        return "UNKNOWN"

    # --- Indicators ---
    # ADX
    adx = _compute_adx(df, period=14)

    # 50-period moving average
    ma_window = 50
    if df["close"].size < ma_window:
        ma50 = df["close"].expanding().mean().iloc[-1]
    else:
        ma50 = df["close"].rolling(window=ma_window).mean().iloc[-1]
    price = float(df["close"].iloc[-1])

    # Bollinger Bands (20-period, 2 std)
    bb_window = 20
    if df["close"].size < bb_window:
        rolling = df["close"].expanding()
    else:
        rolling = df["close"].rolling(window=bb_window)
    mid = rolling.mean().iloc[-1]

    try:
        std = rolling.std().iloc[-1]
    except Exception:
        std = 0.0

    upper_band = float(mid + 2 * std) if pd.notna(mid) and pd.notna(std) else float("inf")
    lower_band = float(mid - 2 * std) if pd.notna(mid) and pd.notna(std) else float("-inf")

    # VIX-equivalent from realized volatility
    vix_equiv = _compute_vix_equivalent(df, lookback=20)

    # --- Regime rules (priority: HIGH_VOLATILITY first) ---
    if vix_equiv > 30.0:
        return "HIGH_VOLATILITY"

    if adx > 25:
        if price > ma50:
            return "TRENDING_UP"
        if price < ma50:
            return "TRENDING_DOWN"

    if adx < 20 and lower_band <= price <= upper_band:
        return "RANGING"

    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Redis caching helpers (15-minute TTL recommended)
# ---------------------------------------------------------------------------

def cache_regime(symbol: str, regime: str, ttl_seconds: int = 900) -> None:
    """Cache the latest regime for a symbol in Redis with a default 15-minute TTL."""
    try:
        client = _get_redis_client()
    except RuntimeError:
        return

    key = f"regime:{symbol.upper()}"
    client.setex(key, ttl_seconds, regime)


def get_cached_regime(symbol: str) -> Optional[str]:
    """Return cached regime for symbol if present, else None."""
    try:
        client = _get_redis_client()
    except RuntimeError:
        return None

    key = f"regime:{symbol.upper()}"
    val = client.get(key)
    if val is None:
        return None
    try:
        return val.decode("utf-8")
    except Exception:
        return None

