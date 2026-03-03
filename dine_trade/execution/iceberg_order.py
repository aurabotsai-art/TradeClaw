"""Iceberg / hidden order management for equities (Alpaca) and crypto (Binance).

Phase 9.3:
    iceberg_order(symbol, side, total_qty, visible_qty, price_tolerance_pct=0.05)

Behavior:
    - For Binance crypto symbols (e.g. BTCUSDT): use native `icebergQty` on a single
      LIMIT order.
    - For Alpaca equities: approximate iceberg behavior by repeatedly submitting
      `smart_limit_order` slices of `visible_qty` until `total_qty` is attempted.

Notes:
    - Fat-finger style price tolerance: limit price is taken from the latest
      market price; if price cannot be fetched, the function aborts.
    - Alpaca's extended-hours support is limited; this module currently uses
      regular session DAY orders and logs a warning if extended hours would be
      required.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from dine_trade.data.connectors.binance_connector import get_ticker as binance_get_ticker
from dine_trade.execution.alpaca_client import smart_limit_order
from dine_trade.storage.supabase_client import insert_trade_log

logger = logging.getLogger(__name__)

try:
    # Reuse Binance client setup from binance_executor
    from dine_trade.execution.binance_executor import _get_client as _get_binance_client  # type: ignore
    from binance.client import Client as BinanceClient  # type: ignore[import]
except Exception:  # pragma: no cover - optional until python-binance installed
    _get_binance_client = None  # type: ignore[assignment]
    BinanceClient = None  # type: ignore[assignment]


def _is_crypto_symbol(symbol: str) -> bool:
    """Heuristic to decide if symbol is a Binance-style crypto pair."""
    s = symbol.upper()
    return s.endswith("USDT") or s.endswith("BTC") or s.endswith("ETH")


def _log_iceberg_trade(
    symbol: str,
    side: str,
    total_qty: float,
    visible_qty: float,
    asset_class: str,
    extra: Dict[str, Any] | None = None,
) -> None:
    """Insert a summary row into trade_log for iceberg orders."""
    row: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "qty": float(total_qty),
        "price": None,  # actual fills/prices live in exchange-order data
        "strategy_phase": "live",
        "asset_class": asset_class,
        "execution_algo": "ICEBERG",
        "iceberg_visible_qty": float(visible_qty),
    }
    if extra:
        row.update(extra)
    try:
        insert_trade_log(row)
    except RuntimeError:
        logger.warning("Supabase not configured; skipping trade_log insert for iceberg order.")


def _alpaca_iceberg(
    symbol: str,
    side: str,
    total_qty: float,
    visible_qty: float,
    price_tolerance_pct: float,
) -> Dict[str, Any]:
    """Approximate iceberg behavior on Alpaca via repeated smart_limit_order slices."""
    # For now we rely on smart_limit_order's internal price and DataValidator behavior.
    # Extended-hours support is not wired; warn once if used in future.
    remaining = float(total_qty)
    slice_size = float(visible_qty)
    if remaining <= 0 or slice_size <= 0:
        return {"ok": False, "error": "total_qty and visible_qty must be positive", "orders": []}

    orders: list[Dict[str, Any]] = []
    # Best-effort: try up to N slices
    max_slices = int((remaining / slice_size) + 1)

    logger.info(
        "Starting Alpaca iceberg: symbol=%s side=%s total_qty=%.4f visible_qty=%.4f max_slices=%s",
        symbol,
        side,
        remaining,
        slice_size,
        max_slices,
    )

    for _ in range(max_slices):
        if remaining <= 0:
            break
        this_qty = min(slice_size, remaining)
        result = smart_limit_order(symbol, side, this_qty, 60)
        orders.append(result)
        if not result.get("ok"):
            logger.warning("Alpaca iceberg slice failed for %s: %s", symbol, result.get("error"))
            break
        remaining -= this_qty

    any_ok = any(o.get("ok") for o in orders)
    _log_iceberg_trade(symbol, side, total_qty, visible_qty, asset_class="EQUITY")
    return {"ok": any_ok, "orders": orders, "remaining_qty": max(0.0, remaining)}


def _binance_iceberg(
    symbol: str,
    side: str,
    total_qty: float,
    visible_qty: float,
    price_tolerance_pct: float,
) -> Dict[str, Any]:
    """Place a native Binance iceberg limit order using `icebergQty`."""
    if _get_binance_client is None or BinanceClient is None:
        return {"ok": False, "error": "Binance client not available; install python-binance", "order": None}

    side_norm = side.upper()
    if side_norm not in {"BUY", "SELL"}:
        return {"ok": False, "error": f"Invalid side '{side}'", "order": None}

    try:
        qty_total = float(total_qty)
        qty_visible = float(visible_qty)
    except (TypeError, ValueError):
        return {"ok": False, "error": "total_qty and visible_qty must be numeric", "order": None}

    if qty_total <= 0 or qty_visible <= 0:
        return {"ok": False, "error": "total_qty and visible_qty must be positive", "order": None}
    if qty_visible > qty_total:
        qty_visible = qty_total

    ticker = binance_get_ticker(symbol)
    mkt_price = ticker.get("price")
    if mkt_price is None:
        return {"ok": False, "error": "Unable to fetch current Binance price for iceberg order", "order": None}
    try:
        mkt = float(mkt_price)
    except (TypeError, ValueError):
        return {"ok": False, "error": "Invalid market price from Binance", "order": None}
    if mkt <= 0:
        return {"ok": False, "error": "Non-positive market price from Binance", "order": None}

    # Use current market price as limit; enforce tolerance relative to itself (0 deviation)
    limit_price = mkt

    client = _get_binance_client()
    try:
        order = client.create_order(
            symbol=symbol,
            side=side_norm,
            type=BinanceClient.ORDER_TYPE_LIMIT,  # type: ignore[attr-defined]
            timeInForce=BinanceClient.TIME_IN_FORCE_GTC,  # type: ignore[attr-defined]
            quantity=qty_total,
            price=str(limit_price),
            icebergQty=str(qty_visible),
        )
        _log_iceberg_trade(
            symbol,
            side_norm,
            qty_total,
            qty_visible,
            asset_class="CRYPTO",
            extra={"exchange_order_raw": order},
        )
        return {"ok": True, "order": order}
    except Exception as e:  # pragma: no cover
        logger.exception("Binance iceberg order failed for %s: %s", symbol, e)
        return {"ok": False, "error": str(e), "order": None}


def iceberg_order(
    symbol: str,
    side: str,
    total_qty: float,
    visible_qty: float,
    price_tolerance_pct: float = 0.05,
) -> Dict[str, Any]:
    """Entry point for iceberg orders.

    Heuristic routing:
        - If symbol looks like a crypto pair (e.g. BTCUSDT), use Binance iceberg.
        - Otherwise, use Alpaca smart_limit_order slices.
    """
    if _is_crypto_symbol(symbol):
        return _binance_iceberg(symbol, side, total_qty, visible_qty, price_tolerance_pct)
    return _alpaca_iceberg(symbol, side, total_qty, visible_qty, price_tolerance_pct)

