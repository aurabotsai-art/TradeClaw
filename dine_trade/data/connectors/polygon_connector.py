"""Polygon.io data connector. Optional secondary data source for failover.

This module provides minimal helpers to fetch OHLCV and latest price from
Polygon's REST API. It is only used when POLYGON_API_KEY is configured.

NOTE: Polygon symbol formats differ slightly from Alpaca (e.g. "NVDA" vs
"X:NVDA" for some endpoints). Here we assume US stock tickers like "NVDA" and
map them to the standard Polygon "NVDA" ticker in the aggregates endpoint.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import pandas as pd
import requests

from dine_trade.config.settings import POLYGON_API_KEY

POLYGON_BASE_URL = os.getenv("POLYGON_BASE_URL", "https://api.polygon.io")


def _require_key() -> str:
    if not POLYGON_API_KEY:
        raise RuntimeError("POLYGON_API_KEY is not configured.")
    return POLYGON_API_KEY


def get_ohlcv(symbol: str, days: int = 100) -> pd.DataFrame:
    """Fetch daily OHLCV bars for the past `days` calendar days from Polygon.

    Returns a DataFrame with columns: date, open, high, low, close, volume.
    """
    api_key = _require_key()
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days)

    # Polygon aggregates API: /v2/aggs/ticker/{symbol}/range/1/day/{from}/{to}
    url = (
        f"{POLYGON_BASE_URL}/v2/aggs/ticker/{symbol}/range/1/day/"
        f"{start.isoformat()}/{end.isoformat()}"
    )
    params: Dict[str, Any] = {"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": api_key}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    if not results:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

    rows = []
    for r in results:
        # Polygon timestamps are in milliseconds since epoch
        ts = r.get("t")
        dt = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc) if ts is not None else None
        rows.append(
            {
                "date": dt.date().isoformat() if dt else None,
                "open": r.get("o"),
                "high": r.get("h"),
                "low": r.get("l"),
                "close": r.get("c"),
                "volume": r.get("v"),
            }
        )

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["date", "close"]).reset_index(drop=True)
    return df


def get_latest_price(symbol: str) -> float | None:
    """Fetch latest trade price from Polygon; returns None on failure."""
    api_key = _require_key()
    # Using snapshot endpoint: /v2/last/trade/{symbol}
    url = f"{POLYGON_BASE_URL}/v2/last/trade/{symbol}"
    params = {"apiKey": api_key}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
    except requests.RequestException:
        return None
    data = resp.json()
    price = data.get("results", {}).get("p") or data.get("price")
    try:
        return float(price)
    except (TypeError, ValueError):
        return None

