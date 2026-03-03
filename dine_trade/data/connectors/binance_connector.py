"""Binance crypto connector (REST).

Provides minimal OHLCV, ticker, and order book access via python-binance.

- get_ohlcv(symbol, interval="1h", limit=200) -> pd.DataFrame
  * Uses python-binance `get_klines`.
  * Symbol format: BTCUSDT, ETHUSDT, SOLUSDT, etc.

- get_ticker(symbol) -> dict
  * Latest price, 24h volume, percent change.

- get_order_book(symbol, limit=20) -> dict
  * Bid/ask ladder (top N levels).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)

try:
    from binance.client import Client as BinanceClient  # type: ignore[import]
except ImportError:  # pragma: no cover - optional dependency
    BinanceClient = None  # type: ignore[assignment]


def _get_client() -> "BinanceClient":
    """Return an unauthenticated Binance client (public market data only)."""
    if BinanceClient is None:
        raise RuntimeError("python-binance is not installed; pip install python-binance")
    # Public market data does not require API keys
    return BinanceClient()


def get_ohlcv(symbol: str, interval: str = "1h", limit: int = 200) -> pd.DataFrame:
    """Fetch OHLCV klines for a crypto symbol.

    Returns DataFrame with columns:
        ["open_time", "open", "high", "low", "close", "volume", "close_time"].
    """
    client = _get_client()
    try:
        klines: List[List[Any]] = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    except Exception as e:  # pragma: no cover - remote errors
        logger.warning("Binance get_klines failed for %s: %s", symbol, e)
        return pd.DataFrame(
            columns=["open_time", "open", "high", "low", "close", "volume", "close_time"]
        )

    if not klines:
        return pd.DataFrame(
            columns=["open_time", "open", "high", "low", "close", "volume", "close_time"]
        )

    rows = []
    for k in klines:
        # See Binance docs for kline array structure
        open_time = pd.to_datetime(k[0], unit="ms")
        open_p = float(k[1])
        high_p = float(k[2])
        low_p = float(k[3])
        close_p = float(k[4])
        vol = float(k[5])
        close_time = pd.to_datetime(k[6], unit="ms")
        rows.append(
            {
                "open_time": open_time,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": vol,
                "close_time": close_time,
            }
        )

    return pd.DataFrame(rows)


def get_ticker(symbol: str) -> Dict[str, Any]:
    """Return latest price, 24h volume, and percent change for symbol."""
    client = _get_client()
    try:
        ticker = client.get_ticker(symbol=symbol)
    except Exception as e:  # pragma: no cover
        logger.warning("Binance get_ticker failed for %s: %s", symbol, e)
        return {
            "symbol": symbol,
            "price": None,
            "volume_24h": None,
            "percent_change_24h": None,
        }

    try:
        price = float(ticker.get("lastPrice"))
    except (TypeError, ValueError):
        price = None
    try:
        vol_24h = float(ticker.get("volume"))
    except (TypeError, ValueError):
        vol_24h = None
    try:
        pct_change = float(ticker.get("priceChangePercent"))
    except (TypeError, ValueError):
        pct_change = None

    return {
        "symbol": symbol,
        "price": price,
        "volume_24h": vol_24h,
        "percent_change_24h": pct_change,
        "raw": ticker,
    }


def get_order_book(symbol: str, limit: int = 20) -> Dict[str, Any]:
    """Return a simple bid/ask ladder for symbol."""
    client = _get_client()
    try:
        ob = client.get_order_book(symbol=symbol, limit=limit)
    except Exception as e:  # pragma: no cover
        logger.warning("Binance get_order_book failed for %s: %s", symbol, e)
        return {"symbol": symbol, "bids": [], "asks": []}

    # Normalize bids/asks into floats
    bids = []
    for price_str, qty_str in ob.get("bids", []):
        try:
            bids.append((float(price_str), float(qty_str)))
        except (TypeError, ValueError):
            continue

    asks = []
    for price_str, qty_str in ob.get("asks", []):
        try:
            asks.append((float(price_str), float(qty_str)))
        except (TypeError, ValueError):
            continue

    return {
        "symbol": symbol,
        "bids": bids,
        "asks": asks,
    }


