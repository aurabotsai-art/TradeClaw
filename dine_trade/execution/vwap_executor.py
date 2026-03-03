from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from dine_trade.execution.alpaca_client import smart_limit_order
from dine_trade.storage.redis_client import _get_client as _get_redis_client


logger = logging.getLogger(__name__)


def _fetch_recent_trades(symbol: str, since_ms: float) -> List[Dict[str, Any]]:
    """Fetch recent trade ticks for symbol from Redis sorted set."""
    try:
        client = _get_redis_client()
    except RuntimeError:
        logger.warning("Redis not available; VWAP executor falling back to single slice.")
        return []

    key = f"ticks:{symbol}"
    # Get ticks with score (timestamp in ms) >= since_ms
    raw = client.zrangebyscore(key, min=since_ms, max="+inf")
    trades: List[Dict[str, Any]] = []
    for b in raw:
        try:
            tick = json.loads(b)
        except Exception:
            continue
        if not isinstance(tick, dict):
            continue
        # Polygon trade event type is 'T'
        if tick.get("ev") != "T":
            continue
        trades.append(tick)
    return trades


def _aggregate_volume_and_vwap(trades: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute interval volume and price*volume sum for VWAP."""
    vol = 0.0
    pv = 0.0
    for t in trades:
        price = t.get("p")
        size = t.get("s")
        try:
            price_f = float(price)
            size_f = float(size)
        except (TypeError, ValueError):
            continue
        if price_f <= 0 or size_f <= 0:
            continue
        vol += size_f
        pv += price_f * size_f
    return {"volume": vol, "pv": pv}


def vwap_order(
    symbol: str,
    side: str,
    total_qty: float,
    duration_minutes: int,
    *,
    participation_rate: float = 0.10,
    interval_seconds: int = 60,
) -> List[Dict[str, Any]]:
    """
    Execute a VWAP-style order using Alpaca, guided by real-time volume from Polygon ticks.

    Args:
        symbol: Equity symbol (e.g. "NVDA").
        side: "buy" or "sell".
        total_qty: Total quantity to execute over the full duration.
        duration_minutes: Overall duration for the schedule.
        participation_rate: Target fraction of market volume per interval (e.g. 0.10 = 10%).
        interval_seconds: Length of each slice interval in seconds.

    Returns:
        List of per-slice execution reports (one dict per attempted slice).

    Notes:
        - Requires Polygon WS streamer writing trade ticks into Redis `ticks:{symbol}`.
        - If Redis/ticks are unavailable, falls back to a single smart_limit_order.
    """
    try:
        total_qty = float(total_qty)
    except (TypeError, ValueError):
        raise ValueError("total_qty must be numeric")
    if total_qty <= 0:
        raise ValueError("total_qty must be positive")

    side_norm = (side or "").lower()
    if side_norm not in {"buy", "sell"}:
        raise ValueError("side must be 'buy' or 'sell'")

    duration_seconds = max(1, int(duration_minutes * 60))
    interval_seconds = max(10, int(interval_seconds))
    num_intervals = max(1, duration_seconds // interval_seconds)

    reports: List[Dict[str, Any]] = []
    remaining = float(total_qty)

    # Benchmark accumulators for realized VWAP
    total_pv = 0.0
    total_vol = 0.0

    start = datetime.now(timezone.utc)
    last_ts_ms = start.timestamp() * 1000.0

    for i in range(num_intervals):
        if remaining <= 0:
            break

        interval_start = datetime.now(timezone.utc)
        interval_end = interval_start + timedelta(seconds=interval_seconds)

        # 1) Look at recent market volume since last interval
        trades = _fetch_recent_trades(symbol, since_ms=last_ts_ms)
        interval_stats = _aggregate_volume_and_vwap(trades)
        interval_vol = interval_stats["volume"]
        interval_pv = interval_stats["pv"]

        # Update last_ts_ms to now for next interval
        last_ts_ms = datetime.now(timezone.utc).timestamp() * 1000.0

        # 2) Decide slice size based on participation rate
        if interval_vol > 0:
            target_slice = participation_rate * interval_vol
            # Clip to remaining
            slice_qty = min(remaining, max(1.0, target_slice))
        else:
            # No recent volume; place a small probing slice
            slice_qty = min(remaining, max(1.0, total_qty / num_intervals))

        # 3) Submit smart limit slice via Alpaca
        logger.info(
            "VWAP slice %s/%s for %s: interval_vol=%.2f, slice_qty=%.4f (remaining=%.4f)",
            i + 1,
            num_intervals,
            symbol,
            interval_vol,
            slice_qty,
            remaining,
        )
        order_res = smart_limit_order(symbol=symbol, side=side_norm, qty=slice_qty)

        # Extract effective fill price if available
        fill_price = None
        raw_order = order_res.get("order") or {}
        try:
            # Alpaca REST order may expose avg_fill_price; else fall back to limit_price
            fill_price = float(raw_order.get("filled_avg_price") or raw_order.get("avg_fill_price"))
        except Exception:
            fill_price = float(order_res.get("limit_price") or 0.0) or None

        # Update benchmark accumulators using market trades during this interval
        if interval_vol > 0 and interval_pv > 0:
            total_pv += interval_pv
            total_vol += interval_vol

        # Compute current benchmark VWAP and slippage for this slice
        benchmark_vwap = total_pv / total_vol if total_vol > 0 else None

        slippage = None
        if fill_price is not None and benchmark_vwap is not None:
            if side_norm == "buy":
                slippage = fill_price - benchmark_vwap
            else:
                slippage = benchmark_vwap - fill_price

        report = {
            "slice_index": i,
            "requested_qty": slice_qty,
            "remaining_after": max(0.0, remaining - slice_qty),
            "interval_volume": interval_vol,
            "fill_price": fill_price,
            "order_result": order_res,
            "benchmark_vwap": benchmark_vwap,
            "slippage": slippage,
            "interval_start": interval_start.isoformat(),
            "interval_end": interval_end.isoformat(),
        }
        reports.append(report)

        # Log slippage delta if we have it
        if slippage is not None:
            logger.info(
                "VWAP slice %s/%s for %s: fill_price=%.4f, benchmark_vwap=%.4f, slippage=%.6f",
                i + 1,
                num_intervals,
                symbol,
                fill_price,
                benchmark_vwap,
                slippage,
            )

        remaining -= slice_qty

        # Sleep until next interval boundary
        now = datetime.now(timezone.utc)
        if i < num_intervals - 1:
            sleep_sec = (interval_end - now).total_seconds()
            if sleep_sec > 0:
                time.sleep(sleep_sec)

    return reports

