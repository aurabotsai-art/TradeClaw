"""Real-time PnL and equity curve monitoring.

Functions:
- compute_live_pnl(positions, current_prices) -> dict
    * Realized PnL from trade_log (closed trades) is not fully tracked in this
      module yet; we expose a placeholder realized_pnl=0.0 by default.
    * Unrealized PnL is sum of (current_price - entry_price) * qty for open positions.
    * Net PnL = realized + unrealized - commissions (commissions placeholder=0.0).

The monitoring loop (not exposed as public API here) is responsible for:
- Updating metrics every N seconds.
- Pushing values to Prometheus gauges (if prometheus_client is installed).
- Storing equity snapshots in Supabase `equity_curve` table:
    (timestamp, equity, drawdown_pct)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Mapping

from dine_trade.risk.limits import compute_daily_drawdown
from dine_trade.storage.supabase_client import _get_client as _get_supabase_client  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)

try:
    # Optional Prometheus integration
    from prometheus_client import Gauge  # type: ignore[import]
except ImportError:  # pragma: no cover
    Gauge = None  # type: ignore[assignment]


def compute_live_pnl(
    positions: Mapping[str, Mapping[str, Any]],
    current_prices: Mapping[str, float],
    *,
    realized_pnl: float = 0.0,
    commissions: float = 0.0,
    equity_at_open: float | None = None,
) -> Dict[str, Any]:
    """Compute live PnL and equity given open positions and current prices.

    Parameters:
      - positions: mapping symbol -> position dict with at least:
            {"symbol": str, "qty": float, "entry_price": float}
      - current_prices: mapping symbol -> latest price (float)
      - realized_pnl: realized PnL from closed trades (external input, default 0.0)
      - commissions: cumulative commissions/fees (external input, default 0.0)
      - equity_at_open: optional starting equity for drawdown calculation.

    Returns dict:
      {
        "realized_pnl": float,
        "unrealized_pnl": float,
        "net_pnl": float,
        "gross_exposure": float,
        "equity": float | None,
        "drawdown_pct": float | None,
      }
    """
    unrealized_pnl = 0.0
    gross_exposure = 0.0

    for symbol, pos in positions.items():
        qty = float(pos.get("qty", 0.0) or 0.0)
        entry_price = float(pos.get("entry_price", 0.0) or 0.0)
        if qty == 0 or entry_price == 0:
            continue

        side = str(pos.get("side") or ("BUY" if qty > 0 else "SELL")).upper()
        current_price = float(current_prices.get(symbol, entry_price) or entry_price)

        # Long: (current - entry) * qty; Short: (entry - current) * |qty|
        if side == "SELL" or qty < 0:
            pnl_pos = (entry_price - current_price) * abs(qty)
        else:
            pnl_pos = (current_price - entry_price) * qty

        unrealized_pnl += pnl_pos
        gross_exposure += abs(current_price * qty)

    net_pnl = float(realized_pnl + unrealized_pnl - commissions)

    equity = None
    drawdown_pct = None
    if equity_at_open is not None:
        equity = float(equity_at_open + net_pnl)
        drawdown_pct = float(compute_daily_drawdown(equity_at_open, equity))

    return {
        "realized_pnl": float(realized_pnl),
        "unrealized_pnl": float(unrealized_pnl),
        "net_pnl": net_pnl,
        "gross_exposure": float(gross_exposure),
        "equity": equity,
        "drawdown_pct": drawdown_pct,
    }


def _push_equity_snapshot_to_supabase(
    equity: float,
    equity_at_open: float,
) -> None:
    """Store an equity snapshot into Supabase `equity_curve` table."""
    try:
        client = _get_supabase_client()
    except Exception:
        return

    ts = datetime.now(timezone.utc).isoformat()
    drawdown_pct = float(compute_daily_drawdown(equity_at_open, equity))

    row: Dict[str, Any] = {
        "timestamp": ts,
        "equity": float(equity),
        "drawdown_pct": drawdown_pct,
    }
    try:
        client.table("equity_curve").insert(row).execute()
    except Exception:
        logger.debug("Failed to insert equity_curve snapshot", exc_info=True)


# Optional Prometheus gauges (created lazily to avoid hard dependency).
_pnl_gauge = None
_equity_gauge = None


def _ensure_prometheus_metrics() -> None:
    global _pnl_gauge, _equity_gauge
    if Gauge is None or _pnl_gauge is not None:
        return
    _pnl_gauge = Gauge("dinetra de_net_pnl", "Net PnL for the trading system")  # type: ignore[assignment]
    _equity_gauge = Gauge("dinetra de_equity", "Current equity for the trading system")  # type: ignore[assignment]


def update_metrics_and_store_equity(
    positions: Mapping[str, Mapping[str, Any]],
    current_prices: Mapping[str, float],
    *,
    realized_pnl: float = 0.0,
    commissions: float = 0.0,
    equity_at_open: float | None = None,
) -> Dict[str, Any]:
    """High-level helper: compute PnL, push Prometheus gauges, store equity.

    Intended to be called periodically (e.g., every 30 seconds) by a scheduler.
    """
    result = compute_live_pnl(
        positions=positions,
        current_prices=current_prices,
        realized_pnl=realized_pnl,
        commissions=commissions,
        equity_at_open=equity_at_open,
    )

    equity = result.get("equity")
    net_pnl = result.get("net_pnl", 0.0)

    # Prometheus
    if Gauge is not None:
        _ensure_prometheus_metrics()
        try:
            if _pnl_gauge is not None:
                _pnl_gauge.set(float(net_pnl))  # type: ignore[call-arg]
            if _equity_gauge is not None and equity is not None:
                _equity_gauge.set(float(equity))  # type: ignore[call-arg]
        except Exception:
            logger.debug("Failed to update Prometheus PnL/equity gauges", exc_info=True)

    # Supabase equity_curve snapshot
    if equity_at_open is not None and equity is not None:
        _push_equity_snapshot_to_supabase(float(equity), float(equity_at_open))

    return result

