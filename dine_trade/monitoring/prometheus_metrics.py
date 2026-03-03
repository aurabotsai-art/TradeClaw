"""Prometheus metrics for DineTrade.

Phase 11.1:
    - Expose metrics endpoint at http://localhost:8000/metrics
    - Track core trading, risk, and system health metrics.

This module is safe to import anywhere; the metrics server is only started
when start_metrics_server() is called.
"""
from __future__ import annotations

import logging
from typing import Optional

try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
except ImportError:  # pragma: no cover - metrics are optional dependency
    Counter = None  # type: ignore[assignment]
    Gauge = None  # type: ignore[assignment]
    Histogram = None  # type: ignore[assignment]
    start_http_server = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_server_started: bool = False

# Metrics (initialized lazily)
trades_total: Optional[Counter] = None  # type: ignore[assignment]
pnl_gauge: Optional[Gauge] = None  # type: ignore[assignment]
drawdown_gauge: Optional[Gauge] = None  # type: ignore[assignment]
agent_latency: Optional[Histogram] = None  # type: ignore[assignment]
ws_reconnects: Optional[Counter] = None  # type: ignore[assignment]
order_fill_rate: Optional[Gauge] = None  # type: ignore[assignment]
slippage_avg: Optional[Gauge] = None  # type: ignore[assignment]


def _ensure_metrics_initialized() -> None:
    """Create Prometheus metric objects if prometheus_client is installed."""
    global trades_total, pnl_gauge, drawdown_gauge, agent_latency
    global ws_reconnects, order_fill_rate, slippage_avg

    if Counter is None or Gauge is None or Histogram is None:
        logger.warning("prometheus_client not installed; metrics will be no-ops.")
        return

    if trades_total is not None:
        return

    trades_total = Counter(
        "trades_total",
        "Total trades",
        ["symbol", "side", "asset_class"],
    )
    pnl_gauge = Gauge("daily_pnl_usd", "Current day PnL in USD")
    drawdown_gauge = Gauge("current_drawdown_pct", "Current drawdown %")
    agent_latency = Histogram(
        "agent_latency_seconds",
        "Agent response time",
        ["agent_name"],
    )
    ws_reconnects = Counter(
        "ws_reconnect_total",
        "WebSocket reconnection count",
        ["stream"],
    )
    order_fill_rate = Gauge(
        "order_fill_rate_pct",
        "% of limit orders that filled",
    )
    slippage_avg = Gauge(
        "avg_slippage_bps",
        "Average slippage in basis points",
    )


def start_metrics_server(port: int = 8000) -> None:
    """Start Prometheus metrics HTTP server on the given port.

    Call this once at bot startup, e.g. from run_live.py:

        from dine_trade.monitoring.prometheus_metrics import start_metrics_server
        start_metrics_server(8000)
    """
    global _server_started
    _ensure_metrics_initialized()
    if start_http_server is None:
        logger.warning("prometheus_client not installed; cannot start metrics server.")
        return
    if _server_started:
        return
    start_http_server(port)
    _server_started = True
    logger.info("Prometheus metrics server started on port %s", port)


# Convenience wrappers

def inc_trades_total(symbol: str, side: str, asset_class: str, amount: float = 1.0) -> None:
    _ensure_metrics_initialized()
    if trades_total is None:
        return
    trades_total.labels(symbol=symbol, side=side, asset_class=asset_class).inc(amount)


def set_daily_pnl(pnl_usd: float) -> None:
    _ensure_metrics_initialized()
    if pnl_gauge is None:
        return
    pnl_gauge.set(float(pnl_usd))


def set_drawdown(drawdown_pct: float) -> None:
    _ensure_metrics_initialized()
    if drawdown_gauge is None:
        return
    drawdown_gauge.set(float(drawdown_pct))


def observe_agent_latency(agent_name: str, seconds: float) -> None:
    _ensure_metrics_initialized()
    if agent_latency is None:
        return
    agent_latency.labels(agent_name=agent_name).observe(float(seconds))


def inc_ws_reconnect(stream_name: str, amount: float = 1.0) -> None:
    _ensure_metrics_initialized()
    if ws_reconnects is None:
        return
    ws_reconnects.labels(stream=stream_name).inc(amount)


def set_order_fill_rate(fill_rate_pct: float) -> None:
    _ensure_metrics_initialized()
    if order_fill_rate is None:
        return
    order_fill_rate.set(float(fill_rate_pct))


def set_slippage_avg(slippage_bps: float) -> None:
    _ensure_metrics_initialized()
    if slippage_avg is None:
        return
    slippage_avg.set(float(slippage_bps))

