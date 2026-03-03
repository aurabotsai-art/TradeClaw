"""Binance WebSocket connector: live crypto trades, candles, and order book depth.

Phase 8.2: Use python-binance BinanceSocketManager and publish to Redis.

- Streams:
    * trade (tick trades)
    * kline_1m (live 1m candles)
    * depth (order book, depth 10)
- Redis keys:
    * crypto:trades:{SYMBOL}
    * crypto:klines_1m:{SYMBOL}
    * crypto:depth:{SYMBOL}

Book imbalance example (top 10 levels):

    bid_volume = sum(float(b[1]) for b in order_book["bids"][:10])
    ask_volume = sum(float(a[1]) for a in order_book["asks"][:10])
    imbalance_ratio = bid_volume / (bid_volume + ask_volume)
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Iterable, Dict, Any

logger = logging.getLogger(__name__)

try:
    from binance import AsyncClient  # type: ignore
    from binance import BinanceSocketManager  # type: ignore
except ImportError:  # pragma: no cover - optional until python-binance installed
    AsyncClient = None  # type: ignore[assignment]
    BinanceSocketManager = None  # type: ignore[assignment]

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover
    redis = None  # type: ignore[assignment]


def _get_redis_client() -> "redis.Redis | None":  # type: ignore[name-defined]
    """Return a Redis client or None if redis/URL is not configured."""
    if redis is None:
        logger.warning("redis package not installed; Binance WS will not persist data.")
        return None
    try:
        import os

        url = os.getenv("REDIS_URL", "").strip()
        if not url:
            url = "redis://localhost:6379/0"
        return redis.Redis.from_url(url)
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to create Redis client for Binance WS: %s", e)
        return None


async def _push_json(client, key: str, payload: Dict[str, Any]) -> None:
    """RPUSH JSON payload to Redis, best-effort."""
    if client is None:
        return
    try:
        data = json.dumps(payload, default=str)
        client.rpush(key, data)
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to push to Redis key %s: %s", key, e)


def _normalize_symbols(symbols: Iterable[str] | None) -> list[str]:
    if not symbols:
        return ["BTCUSDT"]
    out = [s.strip().upper() for s in symbols if s and s.strip()]
    return out or ["BTCUSDT"]


async def run_binance_ws_stream(
    symbols: Iterable[str] | None = None,
    max_retries: int = 5,
    backoff_base_seconds: float = 2.0,
) -> None:
    """Run Binance WebSocket streams for trades, 1m klines, and depth for given symbols."""
    syms = _normalize_symbols(symbols)

    if AsyncClient is None or BinanceSocketManager is None:
        logger.error("python-binance is not installed; pip install python-binance to use Binance WS.")
        return

    redis_client = _get_redis_client()

    attempt = 0
    while attempt < max_retries:
        attempt += 1
        client = None
        try:
            logger.info(
                "Starting BinanceSocketManager (attempt %s/%s) for symbols: %s",
                attempt,
                max_retries,
                ", ".join(syms),
            )
            client = await AsyncClient.create()
            bm = BinanceSocketManager(client)

            async def handle_trades(symbol: str):
                key = f"crypto:trades:{symbol}"
                stream_name = symbol.lower()
                async with bm.trade_socket(stream_name) as stream:
                    while True:
                        msg = await stream.recv()
                        await _push_json(redis_client, key, msg)

            async def handle_klines(symbol: str):
                key = f"crypto:klines_1m:{symbol}"
                stream_name = symbol.lower()
                async with bm.kline_socket(stream_name, interval="1m") as stream:
                    while True:
                        msg = await stream.recv()
                        await _push_json(redis_client, key, msg)

            async def handle_depth(symbol: str):
                key = f"crypto:depth:{symbol}"
                stream_name = symbol.lower()
                # depth=10 for top 10 levels
                async with bm.depth_socket(stream_name, depth=BinanceSocketManager.WEBSOCKET_DEPTH_10) as stream:
                    while True:
                        msg = await stream.recv()
                        # Compute top-10 book imbalance
                        bids = msg.get("bids") or msg.get("b") or []
                        asks = msg.get("asks") or msg.get("a") or []
                        try:
                            bid_volume = sum(float(b[1]) for b in bids[:10])
                            ask_volume = sum(float(a[1]) for a in asks[:10])
                            if bid_volume + ask_volume > 0:
                                imbalance_ratio = bid_volume / (bid_volume + ask_volume)
                            else:
                                imbalance_ratio = 0.5
                        except Exception:  # pragma: no cover
                            imbalance_ratio = 0.5
                        msg["imbalance_ratio"] = imbalance_ratio
                        await _push_json(redis_client, key, msg)

            tasks = []
            for sym in syms:
                tasks.append(asyncio.create_task(handle_trades(sym)))
                tasks.append(asyncio.create_task(handle_klines(sym)))
                tasks.append(asyncio.create_task(handle_depth(sym)))

            await asyncio.gather(*tasks)
            logger.info("Binance WS streams exited normally.")
            return
        except Exception as e:  # pragma: no cover - network / API errors
            delay = backoff_base_seconds * (2 ** (attempt - 1))
            logger.warning(
                "Binance WS stream error on attempt %s/%s: %s; retrying in %.1fs",
                attempt,
                max_retries,
                e,
                delay,
            )
            if client is not None:
                try:
                    await client.close_connection()
                except Exception:
                    pass
            if attempt >= max_retries:
                logger.error("Binance WS stream failed after %s attempts; giving up.", max_retries)
                return
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                logger.info("Binance WS stream cancelled during backoff.")
                return

