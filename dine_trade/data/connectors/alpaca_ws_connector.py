"""Alpaca WebSocket connector: live quotes, trades, and minute bars.

Phase 7.1: Use alpaca-py StockDataStream and publish all incoming data
to Redis streams for agent consumption.

Usage (example):

    import asyncio
    from dine_trade.data.connectors.alpaca_ws_connector import run_alpaca_ws_stream

    asyncio.run(run_alpaca_ws_stream())
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Iterable, Sequence

from dine_trade.config.settings import APCA_API_KEY_ID, APCA_API_SECRET_KEY, UNIVERSE_DEFAULT

logger = logging.getLogger(__name__)

try:
    from alpaca.data.live import StockDataStream
except ImportError:  # pragma: no cover - optional until alpaca-py is installed
    StockDataStream = None  # type: ignore[assignment]

try:
    import redis  # direct use for streams
except ImportError:  # pragma: no cover
    redis = None  # type: ignore[assignment]


def _get_redis_client() -> "redis.Redis | None":  # type: ignore[name-defined]
    """Return a Redis client or None if redis/URL is not configured."""
    if redis is None:
        logger.warning("redis package not installed; Alpaca WS will not persist data.")
        return None
    try:
        import os

        url = os.getenv("REDIS_URL", "").strip()
        if not url:
            url = "redis://localhost:6379/0"
        return redis.Redis.from_url(url)
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to create Redis client for Alpaca WS: %s", e)
        return None


async def _push_json(client, key: str, payload: dict) -> None:
    """RPUSH JSON payload to Redis, best-effort."""
    if client is None:
        return
    try:
        data = json.dumps(payload, default=str)
        # Using plain list as "stream" for simplicity: RPUSH key data
        client.rpush(key, data)
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to push to Redis key %s: %s", key, e)


def _normalize_symbols(symbols: Sequence[str] | None) -> list[str]:
    if symbols:
        out = [s.strip().upper() for s in symbols if s and s.strip()]
        return out or list(UNIVERSE_DEFAULT)
    return list(UNIVERSE_DEFAULT)


async def run_alpaca_ws_stream(
    symbols: Iterable[str] | None = None,
    max_retries: int = 5,
    backoff_base_seconds: float = 2.0,
) -> None:
    """
    Run Alpaca StockDataStream for quotes, trades, and bars.

    - Subscribes to quotes (q), trades (t), and minute bars (b) for given symbols.
    - Publishes each event as JSON to Redis:
        quotes:{symbol}, trades:{symbol}, bars:{symbol}
    - Reconnects with exponential backoff up to max_retries on failure.
    """
    syms = _normalize_symbols(list(symbols) if symbols is not None else None)

    if not APCA_API_KEY_ID or not APCA_API_SECRET_KEY:
        logger.error("APCA_API_KEY_ID / APCA_API_SECRET_KEY not set; cannot start Alpaca WS stream.")
        return
    if StockDataStream is None:
        logger.error("alpaca-py is not installed; pip install alpaca-py to use Alpaca WebSocket.")
        return

    redis_client = _get_redis_client()

    attempt = 0
    while attempt < max_retries:
        attempt += 1
        try:
            logger.info(
                "Starting Alpaca StockDataStream (attempt %s/%s) for symbols: %s",
                attempt,
                max_retries,
                ", ".join(syms),
            )
            stream = StockDataStream(APCA_API_KEY_ID, APCA_API_SECRET_KEY)

            async def quote_handler(data) -> None:
                key = f"quotes:{getattr(data, 'symbol', getattr(data, 'S', 'UNKNOWN'))}"
                payload = getattr(data, "dict", None)
                if callable(payload):
                    payload = payload()
                elif hasattr(data, "model_dump"):
                    payload = data.model_dump()
                else:
                    payload = getattr(data, "__dict__", {"raw": str(data)})
                await _push_json(redis_client, key, payload)

            async def trade_handler(data) -> None:
                key = f"trades:{getattr(data, 'symbol', getattr(data, 'S', 'UNKNOWN'))}"
                payload = getattr(data, "dict", None)
                if callable(payload):
                    payload = payload()
                elif hasattr(data, "model_dump"):
                    payload = data.model_dump()
                else:
                    payload = getattr(data, "__dict__", {"raw": str(data)})
                await _push_json(redis_client, key, payload)

            async def bar_handler(data) -> None:
                key = f"bars:{getattr(data, 'symbol', getattr(data, 'S', 'UNKNOWN'))}"
                payload = getattr(data, "dict", None)
                if callable(payload):
                    payload = payload()
                elif hasattr(data, "model_dump"):
                    payload = data.model_dump()
                else:
                    payload = getattr(data, "__dict__", {"raw": str(data)})
                await _push_json(redis_client, key, payload)

            # Subscribe handlers
            stream.subscribe_quotes(quote_handler, *syms)
            stream.subscribe_trades(trade_handler, *syms)
            stream.subscribe_bars(bar_handler, *syms)

            # Run until disconnected or cancelled
            await stream.run()
            logger.info("Alpaca StockDataStream exited normally.")
            return
        except Exception as e:  # pragma: no cover - network / API errors
            delay = backoff_base_seconds * (2 ** (attempt - 1))
            logger.warning(
                "Alpaca WS stream error on attempt %s/%s: %s; retrying in %.1fs",
                attempt,
                max_retries,
                e,
                delay,
            )
            if attempt >= max_retries:
                logger.error("Alpaca WS stream failed after %s attempts; giving up.", max_retries)
                return
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                logger.info("Alpaca WS stream cancelled during backoff.")
                return

