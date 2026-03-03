"""Data Stream Manager.

Master process that launches all live data WebSocket connections as async tasks:

- Alpaca StockDataStream (quotes/trades/bars) -> Redis (via alpaca_ws_connector)
- Alpaca NewsDataStream -> Redis + Sentiment Agent + Supabase (alpaca_news_ws)
- Optional Polygon WebSocket (ticks) -> Redis (polygon_ws_connector)

Responsibilities:
- Start and supervise all streams (with retry/backoff on failure).
- Health monitoring: log when a stream drops and when it is restarted.
- Graceful shutdown on SIGINT/SIGTERM: attempt clean close of all streams.

Usage:

    python -m dine_trade.data.stream_manager

"""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Any, Iterable, Optional

from dine_trade.config.logging_config import setup_logging
from dine_trade.config.settings import UNIVERSE_DEFAULT
from dine_trade.data.connectors.alpaca_ws_connector import run_alpaca_ws_stream
from dine_trade.data.connectors.polygon_ws_connector import start_polygon_ws_for_symbols, PolygonWSClient  # type: ignore[import]
from dine_trade.data.feeds import run_news_stream


logger = setup_logging("dine_trade.stream_manager", log_file_prefix="streams")


async def _supervise_alpaca_ws(stop_event: asyncio.Event, symbols: Iterable[str]) -> None:
    """Supervisor for Alpaca StockDataStream (quotes/trades/bars)."""
    attempt = 0
    while not stop_event.is_set():
        attempt += 1
        try:
            logger.info("Starting Alpaca WS stream (attempt %s)", attempt)
            await run_alpaca_ws_stream(symbols=symbols)
            if not stop_event.is_set():
                logger.warning("Alpaca WS stream exited unexpectedly; will restart.")
        except asyncio.CancelledError:
            logger.info("Alpaca WS supervisor cancelled; shutting down.")
            break
        except Exception as e:
            logger.exception("Alpaca WS stream crashed: %s", e)

        # Backoff before restart, unless shutting down
        if stop_event.is_set():
            break
        delay = min(30, 2 * attempt)
        logger.info("Restarting Alpaca WS stream in %ss", delay)
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            break


async def _supervise_news_ws(stop_event: asyncio.Event, symbols: Iterable[str]) -> None:
    """Supervisor for Alpaca NewsDataStream."""
    attempt = 0
    while not stop_event.is_set():
        attempt += 1
        try:
            logger.info("Starting Alpaca News WS stream (attempt %s)", attempt)
            await run_news_stream(universe=symbols)
            if not stop_event.is_set():
                logger.warning("News WS stream exited unexpectedly; will restart.")
        except asyncio.CancelledError:
            logger.info("News WS supervisor cancelled; shutting down.")
            break
        except Exception as e:
            logger.exception("News WS stream crashed: %s", e)

        if stop_event.is_set():
            break
        delay = min(30, 2 * attempt)
        logger.info("Restarting News WS stream in %ss", delay)
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            break


async def _run_polygon_ws(stop_event: asyncio.Event, symbols: Iterable[str]) -> None:
    """Run Polygon WebSocket client in background thread and monitor for shutdown.

    PolygonWSClient already implements its own reconnect logic. Here we:
      - start the client
      - wait until stop_event is set
      - request a clean stop() on the client
    """
    client: Optional[PolygonWSClient]
    try:
        client = start_polygon_ws_for_symbols(symbols, include_level2=True)
    except Exception as e:
        logger.warning("Polygon WS could not be started: %s", e)
        client = None

    try:
        # Wait until shutdown or cancellation
        await stop_event.wait()
    except asyncio.CancelledError:
        logger.info("Polygon WS watcher cancelled.")
    finally:
        if client is not None:
            logger.info("Stopping Polygon WS client.")
            try:
                client.stop()
            except Exception:
                logger.debug("Error while stopping Polygon WS client", exc_info=True)


async def main(symbols: Iterable[str] | None = None) -> None:
    """Main entrypoint for the data stream manager."""
    if symbols is None:
        symbols = UNIVERSE_DEFAULT
    symbols = [s.upper() for s in symbols]

    logger.info("Starting Data Stream Manager for symbols: %s", ", ".join(symbols))

    stop_event = asyncio.Event()

    # Signal handlers for graceful shutdown (best-effort on non-POSIX platforms)
    loop = asyncio.get_running_loop()

    def _handle_signal(sig: signal.Signals) -> None:
        logger.info("Received signal %s; initiating graceful shutdown.", sig.name)
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal, sig)
        except NotImplementedError:
            # add_signal_handler may not be available on some platforms (e.g. Windows)
            pass

    # Launch supervisors
    alpaca_task = asyncio.create_task(_supervise_alpaca_ws(stop_event, symbols), name="alpaca_ws_supervisor")
    news_task = asyncio.create_task(_supervise_news_ws(stop_event, symbols), name="news_ws_supervisor")
    polygon_task = asyncio.create_task(_run_polygon_ws(stop_event, symbols), name="polygon_ws_watcher")

    tasks = [alpaca_task, news_task, polygon_task]

    try:
        # Wait until a stop is requested
        await stop_event.wait()
        logger.info("Stop event set; cancelling stream tasks.")
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("All stream tasks stopped. Data Stream Manager exiting.")


if __name__ == "__main__":  # pragma: no cover
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted by user.")

