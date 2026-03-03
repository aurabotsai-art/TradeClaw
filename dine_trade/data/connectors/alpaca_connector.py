"""Alpaca data connector: OHLCV bars and latest price (for DataValidator and analysis)."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from dine_trade.config.settings import (
    APCA_API_BASE_URL,
    APCA_API_KEY_ID,
    APCA_API_SECRET_KEY,
)

# Alpaca Data API v2: regular (incl. paper) accounts use data.alpaca.markets.
# data.sandbox.alpaca.markets is only for broker-partner sandbox testing.
def _default_data_base() -> str:
    base = (os.getenv("ALPACA_DATA_API_BASE_URL") or "").strip()
    if base:
        return base
    return "https://data.alpaca.markets"


DATA_API_BASE = _default_data_base()


def _headers() -> dict[str, str]:
    key = (APCA_API_KEY_ID or "").strip()
    secret = (APCA_API_SECRET_KEY or "").strip()
    return {
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret,
    }


def get_ohlcv(symbol: str, days: int = 100) -> pd.DataFrame:
    """Fetch daily OHLCV bars for symbol for the last `days` calendar days.
    Returns DataFrame with columns: date, open, high, low, close, volume.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y-%m-%dT00:00:00Z")
    end_str = end.strftime("%Y-%m-%dT23:59:59Z")
    # feed=iex is free; default (sip) can require subscription and return 403
    url = (
        f"{DATA_API_BASE}/v2/stocks/{symbol}/bars"
        f"?timeframe=1Day&start={start_str}&end={end_str}&limit=10000&feed=iex"
    )
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    bars = data.get("bars", [])
    if not bars:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    rows = [
        {
            "date": b["t"][:10],
            "open": float(b["o"]),
            "high": float(b["h"]),
            "low": float(b["l"]),
            "close": float(b["c"]),
            "volume": int(b["v"]),
        }
        for b in bars
    ]
    return pd.DataFrame(rows)


def get_latest_price_from_bars(symbol: str) -> float | None:
    """Latest close price from the most recent daily bar. For DataValidator (source A)."""
    df = get_ohlcv(symbol, days=5)
    if df.empty:
        return None
    return float(df.iloc[-1]["close"])


def get_latest_quote_mid(symbol: str) -> tuple[float | None, float | None, float | None]:
    """Latest quote from Alpaca. Returns (bid, ask, mid). Alpaca: bp=bid price, ap=ask price."""
    url = f"{DATA_API_BASE}/v2/stocks/{symbol}/quotes/latest?feed=iex"
    resp = requests.get(url, headers=_headers(), timeout=10)
    if not resp.ok:
        return None, None, None
    data = resp.json()
    q = data.get("quote", {})
    bp = q.get("bp") and float(q["bp"]) or None
    ap = q.get("ap") and float(q["ap"]) or None
    if bp is None and ap is None:
        return None, None, None
    mid = (bp + ap) / 2 if (bp and ap) else (bp or ap)
    return bp, ap, mid


def get_latest_price(symbol: str) -> float | None:
    """Latest price: quote mid if available, else last bar close. For OHLCV and DataValidator."""
    bid, ask, mid = get_latest_quote_mid(symbol)
    if mid is not None:
        return mid
    return get_latest_price_from_bars(symbol)
