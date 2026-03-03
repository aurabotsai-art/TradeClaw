"""Polygon.io WebSocket connector for Level 2 / real-time ticks.

Connects to:
    wss://socket.polygon.io/stocks

Subscribes to:
  - Q.*  (quotes)
  - T.*  (trades)
  - A.*  (second aggregates)
  - LQ.* (Level 2 NBBO quotes; requires Polygon Starter+ plan)

For each incoming tick, writes a record into Redis as a sorted-set member:

    ZADD ticks:{symbol} {timestamp} {data}

Where:
  - key:   ticks:{symbol}
  - score: timestamp in milliseconds since epoch
  - data:  raw JSON string for the tick

These Redis ticks can then be used as a **second price source** for the
DataValidator, replacing or complementing slower REST calls.

NOTE:
  - This module expects the `websocket-client` and `redis` packages to be
    installed.
  - You must set POLYGON_API_KEY in your environment.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Iterable, List, Optional

from websocket import WebSocketApp  # type: ignore[import]

from dine_trade.config.settings import POLYGON_API_KEY
from dine_trade.storage.redis_client import _get_client as _get_redis_client


logger = logging.getLogger(__name__)

POLYGON_WS_URL = os.getenv("POLYGON_WS_URL", "wss://socket.polygon.io/stocks")


class PolygonWSClient:
    """Simple Polygon WebSocket client streaming ticks into Redis."""

    def __init__(
        self,
        symbols: Iterable[str],
        *,
        include_level2: bool = True,
    ) -> None:
        if not POLYGON_API_KEY:
            raise RuntimeError("POLYGON_API_KEY must be set for Polygon WebSocket.")

        self.symbols: List[str] = list(symbols)
        self.include_level2 = include_level2
        self._ws: Optional[WebSocketApp] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    # ------------------------------------------------------------------
    # WebSocket handlers
    # ------------------------------------------------------------------

    def _on_open(self, ws: WebSocketApp) -> None:  # pragma: no cover - network I/O
        logger.info("Polygon WS opened; authenticating.")
        auth_msg = {"action": "auth", "params": POLYGON_API_KEY}
        ws.send(json.dumps(auth_msg))

        # Build params string for subscriptions
        chans: List[str] = []
        for sym in self.symbols:
            chans.append(f"Q.{sym}")
            chans.append(f"T.{sym}")
            chans.append(f"A.{sym}")
            if self.include_level2:
                chans.append(f"LQ.{sym}")
        params = ",".join(chans)
        sub_msg = {"action": "subscribe", "params": params}
        logger.info("Subscribing to Polygon channels: %s", params)
        ws.send(json.dumps(sub_msg))

    def _on_message(self, ws: WebSocketApp, message: str) -> None:  # pragma: no cover
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.warning("Failed to decode Polygon WS message: %s", message[:200])
            return

        if not isinstance(data, list):
            data = [data]

        try:
            redis_client = _get_redis_client()
        except RuntimeError:
            # Redis not configured; just log once and drop ticks
            logger.error("Redis not configured; dropping Polygon WS ticks.")
            self.stop()
            return

        for tick in data:
            if not isinstance(tick, dict):
                continue

            event_type = tick.get("ev")
            symbol = tick.get("sym")
            ts = tick.get("t") or tick.get("S")  # ms epoch for most events
            if not symbol or ts is None:
                continue

            key = f"ticks:{symbol}"
            try:
                score = float(ts)
            except (TypeError, ValueError):
                continue

            payload = json.dumps(tick, separators=(",", ":"))
            try:
                # ZADD key score member
                redis_client.zadd(key, {payload: score})
            except Exception as e:
                logger.warning("Failed to ZADD tick for %s: %s", symbol, e)

    def _on_error(self, ws: WebSocketApp, error: Exception) -> None:  # pragma: no cover
        logger.warning("Polygon WS error: %s", error)

    def _on_close(self, ws: WebSocketApp, code: int, msg: str) -> None:  # pragma: no cover
        logger.info("Polygon WS closed: code=%s msg=%s", code, msg)

    # ------------------------------------------------------------------
    # Public control methods
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the WebSocket in a background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Request the WebSocket loop to stop."""
        self._stop.set()
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass

    def _run_forever(self) -> None:  # pragma: no cover - long-running
        backoff = 1
        while not self._stop.is_set():
            try:
                self._ws = WebSocketApp(
                    POLYGON_WS_URL,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                logger.info("Connecting to Polygon WS at %s", POLYGON_WS_URL)
                self._ws.run_forever()
            except Exception as e:
                logger.warning("Polygon WS connection error: %s", e)

            if self._stop.is_set():
                break

            logger.info("Polygon WS disconnected; reconnecting in %ss", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)


def start_polygon_ws_for_symbols(symbols: Iterable[str], include_level2: bool = True) -> PolygonWSClient:
    """Helper to start a Polygon WS client for given symbols.

    Example:

        from dine_trade.data.connectors.polygon_ws_connector import start_polygon_ws_for_symbols

        client = start_polygon_ws_for_symbols(["NVDA"])
        # client runs in background; main thread can continue
    """
    client = PolygonWSClient(symbols=symbols, include_level2=include_level2)
    client.start()
    return client

