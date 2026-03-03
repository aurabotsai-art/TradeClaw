"""Real-time feature engineering on top of Redis tick streams.

This module consumes ticks from Redis (populated e.g. by the Polygon WebSocket
connector) and computes rolling features for fast agent consumption:

- rolling_vwap(ticks, window_seconds)      -> real-time VWAP
- rolling_rsi(closes, period=14)          -> RSI updated on new bars/ticks
- bid_ask_spread(quote)                   -> spread widening (liquidity warning)
- tick_velocity(ticks, window_seconds=60) -> trades-per-second spike detection

All features are written back to Redis with a short TTL under keys like:

    feat:{symbol}:vwap:{window}
    feat:{symbol}:rsi:{period}
    feat:{symbol}:spread
    feat:{symbol}:tick_velocity:{window}

Design notes:
  - Redis access is synchronous (via redis-py), so all blocking calls are
    executed via asyncio.to_thread(...) to avoid blocking the main event loop.
  - Ticks are expected to be stored in sorted sets by the WS connector:
        ZADD ticks:{symbol} {timestamp_ms} {json_payload}
    where json_payload is a Polygon tick dict.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from dine_trade.storage.redis_client import _get_client as _get_redis_client


logger = logging.getLogger(__name__)

FEATURE_TTL_SECONDS = 10  # short TTL; features are cheap to recompute


@dataclass
class Tick:
    ts_ms: float
    price: float
    size: float
    is_quote: bool = False
    bid: Optional[float] = None
    ask: Optional[float] = None


async def _zrangebyscore(
    key: str,
    min_score: float,
    max_score: float,
) -> List[bytes]:
    """Async wrapper around Redis ZRANGEBYSCORE."""
    try:
        client = _get_redis_client()
    except RuntimeError:
        return []
    return await asyncio.to_thread(client.zrangebyscore, key, min_score, max_score)


async def _set_feature(key: str, value: Any, ttl: int = FEATURE_TTL_SECONDS) -> None:
    """Async wrapper to set a feature key with TTL."""
    try:
        client = _get_redis_client()
    except RuntimeError:
        return
    await asyncio.to_thread(client.set, key, json.dumps(value), "EX", ttl)


def _parse_ticks(raw_members: Iterable[bytes]) -> List[Tick]:
    """Parse raw JSON tick members into Tick objects."""
    ticks: List[Tick] = []
    for raw in raw_members:
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if not isinstance(obj, dict):
            continue

        ts = obj.get("t") or obj.get("S")
        if ts is None:
            continue
        try:
            ts_ms = float(ts)
        except (TypeError, ValueError):
            continue

        ev = obj.get("ev")
        # Trades (T) and aggregates (A) have different fields
        if ev in ("T", "X"):  # trade
            price = obj.get("p")
            size = obj.get("s", 1.0)
            if price is None:
                continue
            try:
                ticks.append(Tick(ts_ms=ts_ms, price=float(price), size=float(size)))
            except (TypeError, ValueError):
                continue
        elif ev == "A":  # second aggregate
            price = obj.get("c") or obj.get("o")
            size = obj.get("v", 1.0)
            if price is None:
                continue
            try:
                ticks.append(Tick(ts_ms=ts_ms, price=float(price), size=float(size)))
            except (TypeError, ValueError):
                continue
        elif ev in ("Q", "LQ"):  # quote / level2
            bid = obj.get("bp")
            ask = obj.get("ap")
            if bid is None or ask is None:
                continue
            try:
                ticks.append(
                    Tick(
                        ts_ms=ts_ms,
                        price=float((bid + ask) / 2.0),
                        size=1.0,
                        is_quote=True,
                        bid=float(bid),
                        ask=float(ask),
                    )
                )
            except (TypeError, ValueError):
                continue

    return ticks


async def compute_rolling_vwap(symbol: str, window_seconds: int = 60) -> Optional[float]:
    """Compute rolling VWAP over the last `window_seconds` of ticks and cache it.

    Uses trades and aggregates (T/A events). VWAP = sum(p * v) / sum(v).
    """
    now_ms = time.time() * 1000.0
    min_score = now_ms - window_seconds * 1000.0
    members = await _zrangebyscore(f"ticks:{symbol}", min_score, now_ms)
    ticks = _parse_ticks(members)
    trades = [t for t in ticks if not t.is_quote]

    if not trades:
        return None

    prices = np.array([t.price for t in trades], dtype=float)
    sizes = np.array([t.size for t in trades], dtype=float)
    denom = sizes.sum()
    if denom <= 0:
        return None
    vwap = float((prices * sizes).sum() / denom)

    key = f"feat:{symbol}:vwap:{window_seconds}"
    await _set_feature(key, {"value": vwap, "ts": datetime.now(timezone.utc).isoformat()})
    return vwap


async def compute_bid_ask_spread(symbol: str) -> Optional[float]:
    """Compute latest bid-ask spread from the most recent quote tick."""
    now_ms = time.time() * 1000.0
    min_score = now_ms - 5_000.0  # last 5 seconds
    members = await _zrangebyscore(f"ticks:{symbol}", min_score, now_ms)
    ticks = _parse_ticks(members)
    quotes = [t for t in ticks if t.is_quote and t.bid is not None and t.ask is not None]
    if not quotes:
        return None
    latest = quotes[-1]
    spread = float(latest.ask - latest.bid)
    key = f"feat:{symbol}:spread"
    await _set_feature(
        key,
        {"value": spread, "bid": latest.bid, "ask": latest.ask, "ts": datetime.now(timezone.utc).isoformat()},
    )
    return spread


def _rsi_from_closes(closes: np.ndarray, period: int = 14) -> Optional[float]:
    if closes.size <= period:
        return None
    delta = np.diff(closes)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    roll_up = gain[-period:].mean()
    roll_down = loss[-period:].mean()
    if roll_down == 0:
        return 100.0
    rs = roll_up / roll_down
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return float(rsi)


async def compute_rolling_rsi(symbol: str, period: int = 14, window_seconds: int = 900) -> Optional[float]:
    """Compute a rolling RSI over recent closes (approx from ticks) and cache it.

    We approximate closes by using trade/aggregate prices from the last
    `window_seconds` seconds, ordered by time.
    """
    now_ms = time.time() * 1000.0
    min_score = now_ms - window_seconds * 1000.0
    members = await _zrangebyscore(f"ticks:{symbol}", min_score, now_ms)
    ticks = _parse_ticks(members)
    trades = [t for t in ticks if not t.is_quote]
    if len(trades) <= period:
        return None

    closes = np.array([t.price for t in trades], dtype=float)
    rsi = _rsi_from_closes(closes, period=period)
    if rsi is None:
        return None

    key = f"feat:{symbol}:rsi:{period}"
    await _set_feature(key, {"value": rsi, "ts": datetime.now(timezone.utc).isoformat()})
    return rsi


async def compute_tick_velocity(symbol: str, window_seconds: int = 60) -> Optional[float]:
    """Compute tick velocity (ticks per second) in the last `window_seconds`."""
    now_ms = time.time() * 1000.0
    min_score = now_ms - window_seconds * 1000.0
    members = await _zrangebyscore(f"ticks:{symbol}", min_score, now_ms)
    count = len(members)
    if window_seconds <= 0:
        return None
    velocity = float(count / float(window_seconds))
    key = f"feat:{symbol}:tick_velocity:{window_seconds}"
    await _set_feature(key, {"value": velocity, "ts": datetime.now(timezone.utc).isoformat()})
    return velocity


async def feature_loop_for_symbol(
    symbol: str,
    *,
    interval_seconds: float = 1.0,
) -> None:
    """Continuously compute features for a single symbol.

    This coroutine is designed to run inside an asyncio event loop. It never
    blocks directly on I/O; all Redis operations are offloaded via
    asyncio.to_thread(...).
    """
    logger.info("Starting feature loop for %s", symbol)
    try:
        while True:
            await asyncio.gather(
                compute_rolling_vwap(symbol, window_seconds=60),
                compute_bid_ask_spread(symbol),
                compute_rolling_rsi(symbol, period=14, window_seconds=900),
                compute_tick_velocity(symbol, window_seconds=60),
            )
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:  # pragma: no cover
        logger.info("Feature loop for %s cancelled.", symbol)
        raise


async def start_feature_loops(symbols: Iterable[str], interval_seconds: float = 1.0) -> None:
    """Start feature loops for multiple symbols concurrently.

    Example:

        import asyncio
        from dine_trade.utils.feature_engineering import start_feature_loops

        asyncio.run(start_feature_loops(["NVDA"]))
    """
    tasks = [
        asyncio.create_task(feature_loop_for_symbol(sym, interval_seconds=interval_seconds))
        for sym in symbols
    ]
    await asyncio.gather(*tasks)

