"""OANDA Forex connector (REST).

Minimal market-data connector using OANDA v20 REST API:

- Instruments: EUR_USD, GBP_USD, USD_JPY, XAU_USD (gold), etc.
- get_ohlcv(instrument, granularity="H1", count=200) -> pd.DataFrame
- get_latest_price(instrument) -> dict with bid/ask/mid
- get_account_summary() -> dict with balance, margin used, NAV, etc.

Auth/config (env):
- OANDA_API_KEY
- OANDA_ACCOUNT_ID
- OANDA_ENVIRONMENT: "practice" (default) or "live"
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

import pandas as pd
import requests

logger = logging.getLogger(__name__)


OANDA_API_KEY = os.getenv("OANDA_API_KEY", "").strip()
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "").strip()
OANDA_ENVIRONMENT = (os.getenv("OANDA_ENVIRONMENT", "practice") or "practice").lower()


def _base_url() -> str:
    if OANDA_ENVIRONMENT == "live":
        return "https://api-fxtrade.oanda.com"
    # default: practice
    return "https://api-fxpractice.oanda.com"


def _headers() -> Dict[str, str]:
    if not OANDA_API_KEY:
        raise RuntimeError("OANDA_API_KEY must be set for OANDA connector.")
    return {"Authorization": f"Bearer {OANDA_API_KEY}"}


def get_ohlcv(
    instrument: str,
    granularity: str = "H1",
    count: int = 200,
) -> pd.DataFrame:
    """Fetch OHLCV candles for an OANDA instrument.

    Returns DataFrame with columns:
        ["time", "open", "high", "low", "close", "volume"].
    """
    try:
        url = f"{_base_url()}/v3/instruments/{instrument}/candles"
        params = {
            "granularity": granularity,
            "count": min(max(count, 1), 5000),
            "price": "M",  # mid prices
        }
        resp = requests.get(url, headers=_headers(), params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:  # pragma: no cover - network/API errors
        logger.warning("OANDA get_ohlcv failed for %s: %s", instrument, e)
        return pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])

    candles = data.get("candles", [])
    if not candles:
        return pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])

    rows = []
    for c in candles:
        if not c.get("complete", True):
            continue
        t = c.get("time")
        mid = c.get("mid", {})
        try:
            rows.append(
                {
                    "time": pd.to_datetime(t),
                    "open": float(mid.get("o")),
                    "high": float(mid.get("h")),
                    "low": float(mid.get("l")),
                    "close": float(mid.get("c")),
                    "volume": float(c.get("volume", 0.0)),
                }
            )
        except (TypeError, ValueError):
            continue

    return pd.DataFrame(rows)


def get_latest_price(instrument: str) -> Dict[str, Any]:
    """Return latest bid/ask/mid for an instrument."""
    try:
        url = f"{_base_url()}/v3/accounts/{OANDA_ACCOUNT_ID}/pricing"
        params = {"instruments": instrument}
        resp = requests.get(url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:  # pragma: no cover
        logger.warning("OANDA get_latest_price failed for %s: %s", instrument, e)
        return {"instrument": instrument, "bid": None, "ask": None, "mid": None, "raw": None}

    prices = data.get("prices", [])
    if not prices:
        return {"instrument": instrument, "bid": None, "ask": None, "mid": None, "raw": data}

    p = prices[0]
    bids = p.get("bids", [])
    asks = p.get("asks", [])

    bid = float(bids[0]["price"]) if bids else None
    ask = float(asks[0]["price"]) if asks else None
    mid = None
    if bid is not None and ask is not None:
        mid = (bid + ask) / 2.0
    elif bid is not None or ask is not None:
        mid = bid or ask

    return {
        "instrument": p.get("instrument", instrument),
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "raw": p,
    }


def get_account_summary() -> Dict[str, Any]:
    """Return account summary: balance, margin used, NAV, and raw payload."""
    if not OANDA_ACCOUNT_ID:
        raise RuntimeError("OANDA_ACCOUNT_ID must be set for get_account_summary.")

    try:
        url = f"{_base_url()}/v3/accounts/{OANDA_ACCOUNT_ID}/summary"
        resp = requests.get(url, headers=_headers(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:  # pragma: no cover
        logger.warning("OANDA get_account_summary failed: %s", e)
        return {"balance": None, "margin_used": None, "nav": None, "raw": None}

    acct = data.get("account", {})
    try:
        balance = float(acct.get("balance"))
    except (TypeError, ValueError):
        balance = None
    try:
        margin_used = float(acct.get("marginUsed"))
    except (TypeError, ValueError):
        margin_used = None
    try:
        nav = float(acct.get("NAV"))
    except (TypeError, ValueError):
        nav = None

    return {
        "balance": balance,
        "margin_used": margin_used,
        "nav": nav,
        "raw": acct,
    }

