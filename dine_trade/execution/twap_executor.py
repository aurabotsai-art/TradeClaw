"""TWAP Executor (Time-Weighted Average Price) for equities via Alpaca smart_limit_order.

twap_order(
    symbol: str,
    side: str,
    total_qty: float,
    duration_minutes: float,
    num_slices: int,
    *,
    consensus_snapshot: dict | None = None,
    parent_order_id: str | None = None,
) -> list[dict]

Logic:
    slice_qty = total_qty / num_slices
    interval = (duration_minutes * 60) / num_slices
    for i in range(num_slices):
        await asyncio.sleep(interval)
        price = get_mid_price(symbol)
        order = smart_limit_order(symbol, side, slice_qty, time_in_force_sec=30)
        log each slice to trade_log with execution_algo="TWAP" and parent_order_id

Notes:
- This implementation uses synchronous smart_limit_order under the hood and wraps
  it with asyncio.to_thread to avoid blocking the event loop.
- Designed for equities via Alpaca only.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional

from dine_trade.execution.alpaca_client import get_latest_quote, smart_limit_order
from dine_trade.storage.trade_logger import log_trade_attempt

logger = logging.getLogger(__name__)


def get_mid_price(symbol: str) -> Optional[float]:
    """Helper to get mid price from Alpaca latest quote."""
    q = get_latest_quote(symbol)
    mid = q.get("mid")
    try:
        return float(mid) if mid is not None else None
    except (TypeError, ValueError):
        return None


async def twap_order(
    symbol: str,
    side: str,
    total_qty: float,
    duration_minutes: float,
    num_slices: int,
    *,
    consensus_snapshot: Optional[Dict[str, Any]] = None,
    parent_order_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Execute a TWAP order using smart_limit_order slices.

    Returns:
        List of per-slice order dicts (as returned by smart_limit_order).
    """
    consensus_snapshot = consensus_snapshot or {}
    if num_slices <= 0:
        raise ValueError("num_slices must be positive")
    if total_qty <= 0:
        raise ValueError("total_qty must be positive")
    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be positive")

    slice_qty = float(total_qty) / float(num_slices)
    interval_seconds = (float(duration_minutes) * 60.0) / float(num_slices)

    # Generate a parent_order_id if not provided
    if not parent_order_id:
        parent_order_id = f"twap_{symbol}_{uuid.uuid4().hex[:12]}"

    logger.info(
        "Starting TWAP order: symbol=%s side=%s total_qty=%.4f slices=%d interval=%.1fs parent_order_id=%s",
        symbol,
        side,
        total_qty,
        num_slices,
        interval_seconds,
        parent_order_id,
    )

    orders: List[Dict[str, Any]] = []

    for i in range(num_slices):
        if i > 0:
            await asyncio.sleep(interval_seconds)

        mid = get_mid_price(symbol)
        if mid is None:
            logger.warning("TWAP slice %d/%d: no mid price for %s; skipping slice.", i + 1, num_slices, symbol)
            continue

        # Execute slice via smart_limit_order in a worker thread
        order_result = await asyncio.to_thread(
            smart_limit_order,
            symbol=symbol,
            side=side,
            qty=slice_qty,
            time_in_force_sec=30,
        )

        orders.append(order_result)

        ok = bool(order_result.get("ok", False))
        limit_price = float(order_result.get("limit_price", mid) or mid)
        order_id = order_result.get("order_id")

        extra: Dict[str, Any] = {
            "execution_algo": "TWAP",
            "parent_order_id": parent_order_id,
            "twap_slice_index": i,
            "twap_num_slices": num_slices,
            "alpaca_order_id": order_id,
            "ok": ok,
        }

        try:
            log_trade_attempt(
                symbol=symbol,
                side=side,
                qty=slice_qty,
                limit_price=limit_price,
                consensus_snapshot=consensus_snapshot,
                strategy_phase="live",
                extra=extra,
            )
        except Exception:
            logger.exception("Failed to log TWAP slice %d for %s", i + 1, symbol)

    logger.info(
        "Completed TWAP order: symbol=%s side=%s total_qty=%.4f slices=%d parent_order_id=%s",
        symbol,
        side,
        total_qty,
        num_slices,
        parent_order_id,
    )
    return orders

