"""Slippage and spread monitor.

Phase 9.9:
    - record_fill(order_id, expected_price, fill_price, side) -> float
    - check_spread_health(symbol) -> bool

Config (defaults):
    - SPREAD_MAX_BPS_EQUITY = 5.0   # basis points
    - SPREAD_MAX_BPS_CRYPTO = 10.0  # basis points
    - SPREAD_MAX_PIPS_FOREX = 3.0   # pips
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

from dine_trade.data.connectors.alpaca_connector import get_latest_quote_mid
from dine_trade.storage.supabase_client import insert_slippage_log

logger = logging.getLogger(__name__)

try:
    from dine_trade.data.connectors.binance_connector import get_order_book as binance_get_order_book
except Exception:  # pragma: no cover - optional dependency
    binance_get_order_book = None  # type: ignore[assignment]

try:
    from dine_trade.data.connectors import oanda_connector  # type: ignore[import]
except Exception:  # pragma: no cover - optional dependency
    oanda_connector = None  # type: ignore[assignment]


SPREAD_MAX_BPS_EQUITY = float(os.getenv("SPREAD_MAX_BPS_EQUITY", "5.0"))
SPREAD_MAX_BPS_CRYPTO = float(os.getenv("SPREAD_MAX_BPS_CRYPTO", "10.0"))
SPREAD_MAX_PIPS_FOREX = float(os.getenv("SPREAD_MAX_PIPS_FOREX", "3.0"))


def _infer_asset_class(symbol: str) -> str:
    s = symbol.upper()
    if s.endswith("USDT") or s.endswith("BTC") or s.endswith("ETH"):
        return "CRYPTO"
    if "_" in s or s.endswith("USD") or s.endswith("JPY") or s.endswith("EUR"):
        return "FOREX"
    return "EQUITY"


def record_fill(
    order_id: Any,
    expected_price: float,
    fill_price: float,
    side: str,
    *,
    symbol: str | None = None,
    asset_class: str | None = None,
    venue: str | None = None,
) -> float:
    """Record slippage for a filled order and log it to Supabase.

    Slippage is defined as:
        slippage = fill_price - expected_price
    (negative = better than expected, positive = worse)
    """
    try:
        exp = float(expected_price)
        fill = float(fill_price)
    except (TypeError, ValueError):
        logger.warning("record_fill: invalid price types for order_id=%s", order_id)
        return 0.0

    slippage = fill - exp

    ac = asset_class or (_infer_asset_class(symbol) if symbol else "UNKNOWN")

    row: Dict[str, Any] = {
        "order_id": str(order_id),
        "symbol": symbol,
        "side": side,
        "expected_price": exp,
        "fill_price": fill,
        "slippage": slippage,
        "asset_class": ac,
        "venue": venue,
    }
    try:
        insert_slippage_log(row)
    except RuntimeError:
        # Supabase not configured; skip remote logging.
        logger.warning("Supabase not configured; skipping slippage_log insert.")

    return slippage


def _equity_spread_health(symbol: str) -> bool:
    bid, ask, mid = get_latest_quote_mid(symbol)
    if mid is None or bid is None or ask is None or mid <= 0:
        logger.warning("check_spread_health: missing Alpaca quote for %s", symbol)
        return False
    spread = float(ask - bid)
    spread_bps = spread / mid * 10_000.0
    if spread_bps > SPREAD_MAX_BPS_EQUITY:
        logger.warning(
            "Equity spread for %s too wide: %.2f bps (max=%.2f)",
            symbol,
            spread_bps,
            SPREAD_MAX_BPS_EQUITY,
        )
        return False
    return True


def _crypto_spread_health(symbol: str) -> bool:
    if binance_get_order_book is None:
        logger.warning("check_spread_health: Binance connector not available for %s", symbol)
        return True  # can't check, don't hard-block
    try:
        ob = binance_get_order_book(symbol, limit=5)  # type: ignore[call-arg]
    except Exception as e:  # pragma: no cover
        logger.warning("check_spread_health: Binance get_order_book failed for %s: %s", symbol, e)
        return False
    bids = ob.get("bids") or []
    asks = ob.get("asks") or []
    if not bids or not asks:
        logger.warning("check_spread_health: empty Binance book for %s", symbol)
        return False
    best_bid = float(bids[0][0])
    best_ask = float(asks[0][0])
    mid = (best_bid + best_ask) / 2.0
    if mid <= 0:
        return False
    spread = best_ask - best_bid
    spread_bps = spread / mid * 10_000.0
    if spread_bps > SPREAD_MAX_BPS_CRYPTO:
        logger.warning(
            "Crypto spread for %s too wide: %.2f bps (max=%.2f)",
            symbol,
            spread_bps,
            SPREAD_MAX_BPS_CRYPTO,
        )
        return False
    return True


def _forex_spread_health(symbol: str) -> bool:
    if oanda_connector is None:
        logger.warning("check_spread_health: OANDA connector not available for %s", symbol)
        return True
    try:
        quote = oanda_connector.get_latest_price(symbol)  # type: ignore[attr-defined]
    except Exception as e:  # pragma: no cover
        logger.warning("check_spread_health: OANDA get_latest_price failed for %s: %s", symbol, e)
        return False
    bid = quote.get("bid")
    ask = quote.get("ask")
    if bid is None or ask is None:
        logger.warning("check_spread_health: missing OANDA bid/ask for %s", symbol)
        return False
    bid_f = float(bid)
    ask_f = float(ask)
    spread = ask_f - bid_f
    spread_pips = spread * 10_000.0
    if spread_pips > SPREAD_MAX_PIPS_FOREX:
        logger.warning(
            "Forex spread for %s too wide: %.2f pips (max=%.2f)",
            symbol,
            spread_pips,
            SPREAD_MAX_PIPS_FOREX,
        )
        return False
    return True


def check_spread_health(symbol: str) -> bool:
    """Return True if current spread is healthy enough to allow new orders.

    - Equities: spread <= SPREAD_MAX_BPS_EQUITY (5 bps default).
    - Crypto: spread <= SPREAD_MAX_BPS_CRYPTO (10 bps default).
    - Forex: spread <= SPREAD_MAX_PIPS_FOREX (3 pips default).
    """
    asset_class = _infer_asset_class(symbol)
    if asset_class == "EQUITY":
        return _equity_spread_health(symbol)
    if asset_class == "CRYPTO":
        return _crypto_spread_health(symbol)
    if asset_class == "FOREX":
        return _forex_spread_health(symbol)
    logger.warning("check_spread_health: unknown asset_class for symbol %s; defaulting to True", symbol)
    return True

