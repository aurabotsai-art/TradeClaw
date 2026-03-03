"""Cross-asset correlation risk limits.

Functions:
- compute_correlation_matrix(positions: dict) -> pd.DataFrame
    * Pulls 30-day returns for all open positions across asset classes.
    * Returns a correlation matrix (pandas DataFrame) of symbol returns.
    * Flags (via caller) when any pair has correlation > 0.85.

- check_total_exposure(positions: dict, equity: float) -> tuple[bool, str]
    * Enforces:
        - Max 40% of capital in any *correlated cluster* (symbols with pairwise
          correlation > 0.85).
        - Max 60% total capital deployed at once (sum of |position notional| / equity).
    * Returns (ok: bool, reason: str).

`positions` is expected to be a dict:

    {
        "AAPL": {"symbol": "AAPL", "asset_type": "equity", "notional": 10000},
        "BTCUSDT": {"symbol": "BTCUSDT", "asset_type": "crypto", "notional": 5000},
        ...
    }

If `asset_type` is missing, we infer from simple heuristics:
    - Contains '_' -> "forex" (e.g. "EUR_USD")
    - Endswith "USDT" -> "crypto"
    - Else -> "equity"
"""

from __future__ import annotations

import logging
from typing import Dict, Iterable, Tuple

import numpy as np
import pandas as pd

from dine_trade.data.connectors import alpaca_connector
from dine_trade.data.connectors import binance_connector
from dine_trade.data.connectors import oanda_connector

logger = logging.getLogger(__name__)


def _infer_asset_type(symbol: str) -> str:
    s = symbol.upper()
    if "_" in s:
        return "forex"
    if s.endswith("USDT"):
        return "crypto"
    return "equity"


def _get_30d_returns(symbol: str, asset_type: str) -> pd.Series:
    """Fetch 30-day returns series for a symbol based on asset_type.

    Returns a pandas Series of percentage returns (float) indexed by datetime.
    On failure, returns an empty Series.
    """
    try:
        if asset_type == "crypto":
            df = binance_connector.get_ohlcv(symbol, interval="1d", limit=40)
            if df is None or getattr(df, "empty", True):
                return pd.Series(dtype=float)
            close = df["close"].astype(float)
            returns = close.pct_change().dropna()
            returns.index = pd.to_datetime(df["close_time"].iloc[1:])
            return returns
        if asset_type == "forex":
            df = oanda_connector.get_ohlcv(symbol, granularity="D", count=40)
            if df is None or getattr(df, "empty", True):
                return pd.Series(dtype=float)
            close = df["close"].astype(float)
            returns = close.pct_change().dropna()
            returns.index = pd.to_datetime(df["time"].iloc[1:])
            return returns
        # default: equity via Alpaca
        df = alpaca_connector.get_ohlcv(symbol, days=40)
        if df is None or getattr(df, "empty", True):
            return pd.Series(dtype=float)
        close = df["close"].astype(float)
        returns = close.pct_change().dropna()
        returns.index = pd.to_datetime(df["date"].iloc[1:])
        return returns
    except Exception as e:  # pragma: no cover - network / API errors
        logger.warning("Failed to fetch 30d returns for %s (%s): %s", symbol, asset_type, e)
        return pd.Series(dtype=float)


def compute_correlation_matrix(positions: Dict[str, Dict]) -> pd.DataFrame:
    """Compute 30-day return correlation matrix for all open positions.

    positions: mapping from symbol to metadata dict (must at least contain notional).
    """
    if not positions:
        return pd.DataFrame()

    returns_dict: Dict[str, pd.Series] = {}
    for symbol, meta in positions.items():
        sym = str(meta.get("symbol") or symbol).upper()
        asset_type = str(meta.get("asset_type") or _infer_asset_type(sym))
        r = _get_30d_returns(sym, asset_type)
        if not r.empty:
            returns_dict[sym] = r

    if len(returns_dict) < 2:
        # Not enough series to compute correlations
        return pd.DataFrame()

    # Align on common dates
    df = pd.DataFrame(returns_dict)
    if df.empty:
        return pd.DataFrame()

    corr = df.corr()
    return corr


def _find_correlated_clusters(corr: pd.DataFrame, threshold: float = 0.85) -> Dict[int, set]:
    """Simple clustering: group symbols where |corr| >= threshold."""
    symbols = list(corr.columns)
    visited = set()
    clusters: Dict[int, set] = {}
    cluster_id = 0

    for i, sym in enumerate(symbols):
        if sym in visited:
            continue
        # Start new cluster with this symbol
        cluster = {sym}
        visited.add(sym)
        for j, other in enumerate(symbols):
            if other in visited or other == sym:
                continue
            try:
                val = corr.loc[sym, other]
            except KeyError:
                continue
            if np.isnan(val):
                continue
            if abs(float(val)) >= threshold:
                cluster.add(other)
                visited.add(other)
        if len(cluster) > 1:
            clusters[cluster_id] = cluster
            cluster_id += 1
    return clusters


def check_total_exposure(positions: Dict[str, Dict], equity: float) -> Tuple[bool, str]:
    """Check cross-asset correlation and total exposure limits.

    Enforces:
      - Max 40% of capital in any correlated cluster.
      - Max 60% total capital deployed (sum of abs(notional) / equity).
    """
    if equity <= 0:
        return False, "Account equity must be positive."
    if not positions:
        return True, "No open positions."

    # Total exposure
    total_notional = 0.0
    symbol_notional: Dict[str, float] = {}
    for symbol, meta in positions.items():
        notional = float(meta.get("notional", 0.0) or 0.0)
        sym = str(meta.get("symbol") or symbol).upper()
        symbol_notional[sym] = notional
        total_notional += abs(notional)

    total_exposure_pct = (total_notional / equity) * 100.0
    if total_exposure_pct > 60.0:
        return False, f"Total exposure {total_exposure_pct:.2f}% exceeds 60% limit."

    # Correlation exposure (cluster based)
    corr = compute_correlation_matrix(positions)
    if corr.empty or len(corr.columns) < 2:
        return True, "Exposure within limits; insufficient data for correlation matrix."

    clusters = _find_correlated_clusters(corr, threshold=0.85)
    if not clusters:
        return True, "Exposure within limits; no correlated clusters above 0.85."

    max_cluster_pct = 0.0
    worst_cluster = None

    for cid, symbols in clusters.items():
        cluster_notional = sum(abs(symbol_notional.get(sym, 0.0)) for sym in symbols)
        cluster_pct = (cluster_notional / equity) * 100.0
        if cluster_pct > max_cluster_pct:
            max_cluster_pct = cluster_pct
            worst_cluster = symbols

    if max_cluster_pct > 40.0 and worst_cluster is not None:
        syms_str = ", ".join(sorted(worst_cluster))
        return (
            False,
            f"Correlated cluster exposure {max_cluster_pct:.2f}% "
            f"exceeds 40% limit for symbols: {syms_str}.",
        )

    return True, "Exposure within cross-asset correlation and total deployment limits."

