"""Binance execution: spot crypto limit/market orders + basic fat-finger checks.

Phase 8.3:
    - place_limit_order(symbol, side, quantity, price) -> dict
    - place_market_order(symbol, side, quantity) -> dict  (emergency closes only)
    - cancel_order(symbol, order_id) -> dict
    - get_position(symbol) -> dict

Testnet mode:
    - Set BINANCE_TESTNET=true in env to route to Binance testnet.

Fat-finger check:
    - Order limit_price must be within 2% of current market price from get_ticker().

Logging:
    - All orders are logged to Supabase trade_log with asset_class="CRYPTO".
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from dine_trade.config.settings import (
    BINANCE_API_KEY,
    BINANCE_API_SECRET,
    BINANCE_TESTNET,
)
from dine_trade.data.connectors.binance_connector import get_ticker
from dine_trade.storage.supabase_client import insert_trade_log

logger = logging.getLogger(__name__)

try:
    from binance.client import Client as BinanceClient  # type: ignore[import]
except ImportError:  # pragma: no cover - optional dependency
    BinanceClient = None  # type: ignore[assignment]


_client: "BinanceClient | None" = None  # type: ignore[name-defined]


def _get_client() -> "BinanceClient":
    """Return an authenticated Binance client for trading."""
    global _client
    if _client is not None:
        return _client

    if BinanceClient is None:
        raise RuntimeError("python-binance is not installed; pip install python-binance")
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        raise RuntimeError("BINANCE_API_KEY/BINANCE_API_SECRET not configured.")

    logger.info("Creating BinanceClient (testnet=%s)", BINANCE_TESTNET)
    _client = BinanceClient(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET, testnet=BINANCE_TESTNET)
    return _client


def _log_trade(
    symbol: str,
    side: str,
    qty: float,
    price: float | None,
    order: Dict[str, Any] | None,
    strategy_phase: str = "live",
) -> None:
    """Insert a trade_log row for a Binance crypto order."""
    row: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "qty": float(qty),
        "price": float(price) if price is not None else None,
        "strategy_phase": strategy_phase,
        "asset_class": "CRYPTO",
    }
    if order:
        order_id = order.get("orderId") or order.get("clientOrderId")
        if order_id is not None:
            row["order_id"] = str(order_id)
        row["exchange_order_raw"] = order  # jsonb column recommended

    try:
        insert_trade_log(row)
    except RuntimeError:
        # Supabase not configured; skip remote logging.
        logger.warning("Supabase not configured; skipping trade_log insert for Binance order.")


def _fat_finger_check(symbol: str, limit_price: float, tolerance_pct: float = 2.0) -> tuple[bool, str | None]:
    """Return (ok, error_message). Ok iff limit_price within tolerance_pct of current price."""
    ticker = get_ticker(symbol)
    current_price = ticker.get("price")
    if current_price is None:
        return False, "Unable to fetch current Binance price for fat-finger check."
    try:
        mkt = float(current_price)
        lp = float(limit_price)
    except (TypeError, ValueError):
        return False, "Invalid price types in fat-finger check."
    if mkt <= 0:
        return False, "Market price is non-positive; fat-finger check failed."

    deviation_pct = abs(lp - mkt) / mkt * 100.0
    if deviation_pct > tolerance_pct:
        return False, f"Limit price deviation {deviation_pct:.2f}% exceeds {tolerance_pct:.2f}% tolerance."
    return True, None


def place_limit_order(symbol: str, side: str, quantity: float, price: float) -> Dict[str, Any]:
    """Place a Binance spot limit order with fat-finger check and logging."""
    side_norm = side.upper()
    if side_norm not in {"BUY", "SELL"}:
        return {"ok": False, "error": f"Invalid side '{side}'", "order": None}
    try:
        qty = float(quantity)
        if qty <= 0:
            return {"ok": False, "error": "quantity must be positive", "order": None}
        limit_price = float(price)
        if limit_price <= 0:
            return {"ok": False, "error": "price must be positive", "order": None}
    except (TypeError, ValueError):
        return {"ok": False, "error": "quantity and price must be numeric", "order": None}

    ok, err = _fat_finger_check(symbol, limit_price)
    if not ok:
        logger.warning("Binance fat-finger check failed for %s: %s", symbol, err)
        return {"ok": False, "error": err, "order": None}

    client = _get_client()
    try:
        order = client.create_order(
            symbol=symbol,
            side=side_norm,
            type=BinanceClient.ORDER_TYPE_LIMIT,  # type: ignore[attr-defined]
            timeInForce=BinanceClient.TIME_IN_FORCE_GTC,  # type: ignore[attr-defined]
            quantity=qty,
            price=str(limit_price),
        )
        _log_trade(symbol, side_norm, qty, limit_price, order)
        return {"ok": True, "order": order}
    except Exception as e:  # pragma: no cover - remote errors
        logger.exception("Binance limit order failed for %s: %s", symbol, e)
        return {"ok": False, "error": str(e), "order": None}


def place_market_order(symbol: str, side: str, quantity: float) -> Dict[str, Any]:
    """Place a Binance market order (emergency closes only). No retries."""
    side_norm = side.upper()
    if side_norm not in {"BUY", "SELL"}:
        return {"ok": False, "error": f"Invalid side '{side}'", "order": None}
    try:
        qty = float(quantity)
        if qty <= 0:
            return {"ok": False, "error": "quantity must be positive", "order": None}
    except (TypeError, ValueError):
        return {"ok": False, "error": "quantity must be numeric", "order": None}

    client = _get_client()
    try:
        order = client.create_order(
            symbol=symbol,
            side=side_norm,
            type=BinanceClient.ORDER_TYPE_MARKET,  # type: ignore[attr-defined]
            quantity=qty,
        )
        # For market orders, we may not know the exact fill price here; log None.
        _log_trade(symbol, side_norm, qty, None, order)
        return {"ok": True, "order": order}
    except Exception as e:  # pragma: no cover
        logger.exception("Binance market order failed for %s: %s", symbol, e)
        return {"ok": False, "error": str(e), "order": None}


def cancel_order(symbol: str, order_id: Any) -> Dict[str, Any]:
    """Cancel an existing Binance order."""
    client = _get_client()
    try:
        resp = client.cancel_order(symbol=symbol, orderId=order_id)
        return {"ok": True, "response": resp}
    except Exception as e:  # pragma: no cover
        logger.warning("Binance cancel_order failed for %s (%s): %s", symbol, order_id, e)
        return {"ok": False, "error": str(e)}


def get_position(symbol: str) -> Dict[str, Any]:
    """Return a simple position snapshot for the base asset of symbol.

    Assumes spot trading with symbols like BTCUSDT, ETHUSDT, etc.
    """
    client = _get_client()
    base_asset = symbol.replace("USDT", "").upper()
    try:
        bal = client.get_asset_balance(asset=base_asset)
    except Exception as e:  # pragma: no cover
        logger.warning("Binance get_asset_balance failed for %s: %s", base_asset, e)
        return {"symbol": symbol, "asset": base_asset, "free": 0.0, "locked": 0.0, "total": 0.0}

    try:
        free = float(bal.get("free", 0.0))
    except (TypeError, ValueError):
        free = 0.0
    try:
        locked = float(bal.get("locked", 0.0))
    except (TypeError, ValueError):
        locked = 0.0

    return {
        "symbol": symbol,
        "asset": base_asset,
        "free": free,
        "locked": locked,
        "total": free + locked,
        "raw": bal,
    }

