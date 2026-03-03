"""Smart Order Routing (SOR) for equities, crypto, and forex.

Phase 9.4:
    - route_order(symbol, side, qty, asset_class) -> str
    - compare_venues(symbol) -> dict

Decision logic:
    - EQUITY: use Alpaca (best execution for retail) if available.
    - CRYPTO: compare Binance spot vs Binance futures spread — route to tighter spread.
    - FOREX: OANDA for retail sizes; log warning if spread > 3 pips.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from dine_trade.data.connectors.alpaca_connector import get_latest_quote_mid

logger = logging.getLogger(__name__)

try:
    from dine_trade.data.connectors.binance_connector import get_order_book as binance_get_order_book
except Exception:  # pragma: no cover - optional dependency
    binance_get_order_book = None  # type: ignore[assignment]

try:
    from dine_trade.data.connectors.oanda_connector import (  # type: ignore[import]
        get_latest_price as oanda_get_latest_price,
    )
except Exception:  # pragma: no cover - optional dependency
    oanda_get_latest_price = None  # type: ignore[assignment]


def _equity_venue(symbol: str) -> Dict[str, Any]:
    """Return Alpaca equity venue spread info."""
    bid, ask, mid = get_latest_quote_mid(symbol)
    if mid is None or bid is None or ask is None:
        return {"available": False}
    spread = float(ask - bid)
    spread_bps = (spread / mid * 10_000) if mid > 0 else None
    return {
        "available": True,
        "venue": "ALPACA",
        "bid": float(bid),
        "ask": float(ask),
        "mid": float(mid),
        "spread": spread,
        "spread_bps": spread_bps,
    }


def _crypto_venues(symbol: str) -> Dict[str, Any]:
    """Return Binance spot/futures spread info for crypto symbol."""
    out: Dict[str, Any] = {}

    # Spot via existing REST order book
    if binance_get_order_book is not None:
        try:
            ob = binance_get_order_book(symbol, limit=5)  # type: ignore[call-arg]
            bids = ob.get("bids") or []
            asks = ob.get("asks") or []
            if bids and asks:
                best_bid = float(bids[0][0])
                best_ask = float(asks[0][0])
                mid = (best_bid + best_ask) / 2.0
                spread = best_ask - best_bid
                spread_bps = (spread / mid * 10_000) if mid > 0 else None
                out["BINANCE_SPOT"] = {
                    "available": True,
                    "venue": "BINANCE_SPOT",
                    "bid": best_bid,
                    "ask": best_ask,
                    "mid": mid,
                    "spread": spread,
                    "spread_bps": spread_bps,
                }
        except Exception as e:  # pragma: no cover
            logger.warning("Failed to fetch Binance spot book for %s: %s", symbol, e)

    # Placeholder for futures venue; can be extended later with futures REST client.
    out.setdefault("BINANCE_FUTURES", {"available": False})

    return out


def _forex_venue(symbol: str) -> Dict[str, Any]:
    """Return OANDA forex venue spread info (best-effort)."""
    if oanda_get_latest_price is None:
        return {"available": False}
    try:
        quote = oanda_get_latest_price(symbol)  # expected dict with bid/ask or mid
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to fetch OANDA price for %s: %s", symbol, e)
        return {"available": False}

    bid = quote.get("bid")
    ask = quote.get("ask")
    mid = quote.get("mid")
    if bid is None or ask is None:
        return {"available": False}
    bid_f = float(bid)
    ask_f = float(ask)
    mid_f = float(mid) if mid is not None else (bid_f + ask_f) / 2.0
    spread = ask_f - bid_f
    # Approximate pips for major pairs with 4 decimal places
    spread_pips = spread * 10_000
    info = {
        "available": True,
        "venue": "OANDA",
        "bid": bid_f,
        "ask": ask_f,
        "mid": mid_f,
        "spread": spread,
        "spread_pips": spread_pips,
    }
    if spread_pips > 3.0:
        logger.warning("OANDA spread for %s is wide: %.2f pips (> 3 pips)", symbol, spread_pips)
    return info


def compare_venues(symbol: str) -> Dict[str, Dict[str, Any]]:
    """Compare bid/ask spreads across available venues for a symbol.

    Returns a dict keyed by venue name:
        {
            "ALPACA": { ... },
            "BINANCE_SPOT": { ... },
            "BINANCE_FUTURES": { ... },
            "OANDA": { ... },
        }
    Some venues may have {"available": False} when data isn't accessible.
    """
    venues: Dict[str, Dict[str, Any]] = {}

    # Alpaca equities
    try:
        venues["ALPACA"] = _equity_venue(symbol)
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to compute Alpaca venue for %s: %s", symbol, e)
        venues["ALPACA"] = {"available": False}

    # Binance crypto
    try:
        venues.update(_crypto_venues(symbol))
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to compute Binance venues for %s: %s", symbol, e)

    # OANDA forex
    try:
        venues["OANDA"] = _forex_venue(symbol)
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to compute OANDA venue for %s: %s", symbol, e)
        venues["OANDA"] = {"available": False}

    return venues


def route_order(symbol: str, side: str, qty: float, asset_class: str) -> str:
    """Route order to venue based on asset_class and spreads.

    Returns a string venue identifier, e.g. "ALPACA", "BINANCE_SPOT", "BINANCE_FUTURES",
    "OANDA", or "UNKNOWN" when routing is not possible.
    """
    asset = asset_class.upper()
    venues = compare_venues(symbol)

    if asset == "EQUITY":
        alpaca = venues.get("ALPACA", {})
        if alpaca.get("available"):
            return "ALPACA"
        return "UNKNOWN"

    if asset == "CRYPTO":
        # Choose Binance venue (spot vs futures) with tighter spread among available ones.
        candidates = []
        for name in ("BINANCE_SPOT", "BINANCE_FUTURES"):
            info = venues.get(name, {})
            if info.get("available") and info.get("spread") is not None:
                candidates.append((info["spread"], name))
        if not candidates:
            return "UNKNOWN"
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    if asset == "FOREX":
        oanda = venues.get("OANDA", {})
        if not oanda.get("available"):
            return "UNKNOWN"
        # Spread warning is already logged in _forex_venue if > 3 pips.
        return "OANDA"

    logger.warning("Unknown asset_class '%s' for symbol %s; cannot route.", asset_class, symbol)
    return "UNKNOWN"

