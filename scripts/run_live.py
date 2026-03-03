"""Production entry point for DineTrade live bot.

Phase 12.5:
  - setup_logging, validate_all_api_keys, check_kill_switch
  - WebSocket stream manager (background)
  - Market hours scheduler
  - Main consensus loop
  - Health check: http://localhost:8080/health -> {"status": "ok", "uptime_s": N}

Run:
  python -m scripts.run_live
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List

# Project root on path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dine_trade.config.logging_config import setup_logging
from dine_trade.config.settings import (
    DAILY_DRAWDOWN_LIMIT_PCT,
    TRADING_ENABLED,
    UNIVERSE_DEFAULT,
)
from dine_trade.data.providers import get_latest_price_with_failover, get_ohlcv_with_failover
from dine_trade.data.feeds import get_recent_headlines
from dine_trade.orchestration.consensus import run_consensus
from dine_trade.agents.executor import run_executor
from dine_trade.risk.limits import (
    build_failure_state,
    compute_daily_drawdown,
    should_trigger_circuit_breaker,
)
from dine_trade.storage.post_mortem import write_post_mortem
from dine_trade.storage.redis_client import get_equity_at_open, set_equity_at_open
from dine_trade.storage.redis_client import get_circuit_breaker_triggered, set_circuit_breaker_triggered

logger = setup_logging("dine_trade.run_live", log_file_prefix="run_live")

# Render sets PORT; default 8080 for local
HEALTH_PORT = int(os.getenv("PORT", os.getenv("HEALTH_PORT", "8080")))
CONSENSUS_INTERVAL_SECONDS = int(os.getenv("CONSENSUS_INTERVAL_SECONDS", "900"))  # 15 min

_start_time: float = 0.0


def _get_health_response() -> Dict[str, Any]:
    return {"status": "ok", "uptime_s": round(time.time() - _start_time, 1)}


class HealthHandler(BaseHTTPRequestHandler):
    """Serves GET /health and GET /metrics on a single port."""

    def do_GET(self):
        if self.path == "/health" or self.path == "/health/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(_get_health_response()).encode("utf-8"))
            return
        if self.path == "/metrics":
            try:
                from prometheus_client import REGISTRY, generate_latest
                body = generate_latest(REGISTRY)
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                self.send_response(503)
                self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        logger.debug(format, *args)


def _run_health_server(port: int) -> None:
    server = HTTPServer(("", port), HealthHandler)
    logger.info("Health server listening on http://localhost:%s/health", port)
    try:
        server.serve_forever()
    except Exception as e:
        logger.warning("Health server stopped: %s", e)


async def setup_logging_async() -> None:
    """Async wrapper for logging setup (already done at import)."""
    pass


def validate_all_api_keys() -> None:
    """Fail fast if any required API key is missing."""
    required: List[tuple[str, str]] = [
        ("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", "").strip()),
        ("APCA_API_KEY_ID", os.getenv("APCA_API_KEY_ID", "").strip()),
        ("APCA_API_SECRET_KEY", os.getenv("APCA_API_SECRET_KEY", "").strip()),
    ]
    missing = [k for k, v in required if not v]
    if missing:
        raise RuntimeError(
            "Missing required environment variables (set in .env or Render dashboard): " + ", ".join(missing)
        )


def check_kill_switch() -> None:
    """Abort if TRADING_ENABLED is false."""
    if not TRADING_ENABLED:
        logger.warning("TRADING_ENABLED is false; exiting (kill switch).")
        sys.exit(0)


async def stream_manager_start_all() -> None:
    """Start all WebSocket streams in the background; returns once tasks are scheduled."""
    from dine_trade.data import stream_manager
    task = asyncio.create_task(stream_manager.main(), name="stream_manager")
    logger.info("Stream manager started (background task %s)", task.get_name())
    # Don't await; let it run in background


async def scheduler_start() -> None:
    """Start the market-hours scheduler (APScheduler)."""
    from dine_trade.deployment.scheduler import create_scheduler
    scheduler = create_scheduler()
    if scheduler is None:
        logger.warning("APScheduler not available; scheduler not started.")
        return
    scheduler.start()
    logger.info("Market hours scheduler started.")


async def consensus_loop() -> None:
    """Main trading loop: run consensus for each symbol on an interval, respect circuit breaker."""
    while True:
        for symbol in UNIVERSE_DEFAULT:
            try:
                await _run_consensus_round(symbol)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.exception("Consensus round failed for %s: %s", symbol, e)
        await asyncio.sleep(CONSENSUS_INTERVAL_SECONDS)


async def _run_consensus_round(symbol: str) -> None:
    """One round of consensus + optional execution for a single symbol."""
    from dine_trade.execution.alpaca_client import get_account

    # Account equity from Alpaca if available
    try:
        account = get_account()
        account_equity = float(getattr(account, "equity", 0) or account.get("equity", 0) or 100_000.0)
    except Exception:
        account_equity = 100_000.0

    if get_circuit_breaker_triggered():
        logger.debug("Circuit breaker still active; skipping consensus for %s.", symbol)
        return

    # Load data
    ohlcv_df = get_ohlcv_with_failover(symbol, days=100)
    headlines = get_recent_headlines(symbol, limit=10)
    if ohlcv_df is None or getattr(ohlcv_df, "empty", True):
        logger.warning("No OHLCV for %s; skipping.", symbol)
        return

    price_from_bars = float(ohlcv_df["close"].iloc[-1])
    latest_mid = get_latest_price_with_failover(symbol)
    if latest_mid is None:
        logger.warning("No latest price for %s; skipping.", symbol)
        return

    positions: List[Dict[str, Any]] = []
    consensus = await run_consensus(
        symbol=symbol,
        account_equity=account_equity,
        positions=positions,
        ohlcv_df=ohlcv_df,
        headlines=headlines,
    )

    logger.info(
        "Consensus %s: approved=%s, reason=%s, suggested_qty=%.4f",
        symbol, consensus.get("approved"), consensus.get("reason"), consensus.get("suggested_qty", 0.0),
    )

    if not consensus.get("approved"):
        return

    equity_at_open = get_equity_at_open() or account_equity
    set_equity_at_open(equity_at_open)
    current_equity = account_equity
    dd_pct = compute_daily_drawdown(equity_at_open, current_equity)

    if should_trigger_circuit_breaker(dd_pct):
        logger.warning("Daily drawdown %.4f%% >= %.4f%% — circuit breaker.", dd_pct, DAILY_DRAWDOWN_LIMIT_PCT)
        set_circuit_breaker_triggered(True)
        failure_state = build_failure_state(
            equity_at_open=equity_at_open,
            current_equity=current_equity,
            positions_snapshot={"positions": positions},
            sentiment_snapshot=consensus.get("agent_results", {}).get("sentiment", {}),
            charts_snapshot=consensus.get("agent_results", {}).get("chartist", {}),
            agent_summary=consensus,
        )
        try:
            write_post_mortem(failure_state)
        except Exception as e:
            logger.exception("Post-mortem write failed: %s", e)
        return

    executor_result = run_executor(
        consensus | {"symbol": symbol},
        price_a=price_from_bars,
        price_b=float(latest_mid),
        account_equity=account_equity,
        daily_drawdown_pct=dd_pct,
    )
    logger.info(
        "Executor %s: status=%s, qty=%.4f, order_id=%s",
        symbol, executor_result.get("status"), executor_result.get("qty", 0.0), executor_result.get("order_id"),
    )


async def main() -> None:
    global _start_time
    _start_time = time.time()

    await setup_logging_async()
    validate_all_api_keys()
    check_kill_switch()

    # Initialize Prometheus metrics (no separate server; we serve /metrics from health port)
    from dine_trade.monitoring.prometheus_metrics import _ensure_metrics_initialized
    _ensure_metrics_initialized()

    # Health + metrics server in background thread
    server_thread = threading.Thread(target=_run_health_server, args=(HEALTH_PORT,), daemon=True)
    server_thread.start()

    await stream_manager_start_all()
    await scheduler_start()
    await consensus_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(0)
