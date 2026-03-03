from __future__ import annotations

"""
Transaction Cost Analysis (TCA) utilities.

Exposes:
    analyze_trade(trade_id) -> dict

Metrics:
  - Implementation shortfall = (arrival_price - fill_price) * qty * side_sign
  - Market impact estimate   = (post_trade_price - pre_trade_price) * qty * side_sign
  - Opportunity cost         = theoretical PnL if unfilled limit would have hit

Assumptions:
  - `trade_log` table in Supabase contains at least:
        id, symbol, side, qty, price, limit_price, arrival_price, status,
        filled_qty, created_at
  - Optional fields for TCA:
        pre_trade_price, post_trade_price
  - `tca_log` table will store per-trade analysis rows.

If some fields are missing, metrics gracefully degrade (set to 0.0 or None).
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from dine_trade.storage.supabase_client import _get_client as _get_supabase_client


def _side_sign(side: str) -> int:
    s = (side or "").lower()
    if s == "buy":
        return 1
    if s == "sell":
        return -1
    return 0


def _to_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if val is None:
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _fetch_trade(trade_id: str) -> Dict[str, Any]:
    """Fetch a single trade_log row by id from Supabase."""
    client = _get_supabase_client()
    resp = (
        client.table("trade_log")
        .select("*")
        .eq("id", trade_id)
        .limit(1)
        .execute()
    )
    data = getattr(resp, "data", None) or resp.data  # type: ignore[attr-defined]
    if not data:
        raise ValueError(f"trade_log id={trade_id} not found")
    return data[0]


def _infer_arrival_price(trade: Dict[str, Any]) -> Optional[float]:
    """
    Infer arrival price for a trade.

    Preferred fields:
      - arrival_price
      - pre_trade_price
      - price (fallback: treat fill price as arrival -> zero shortfall)
    """
    for key in ("arrival_price", "pre_trade_price", "price"):
        if key in trade:
            val = _to_float(trade.get(key))
            if val is not None:
                return val
    return None


def _infer_fill_price(trade: Dict[str, Any]) -> Optional[float]:
    """Infer effective fill price."""
    # Prefer explicit fill_price if present
    for key in ("fill_price", "filled_avg_price", "price", "limit_price"):
        if key in trade:
            val = _to_float(trade.get(key))
            if val is not None:
                return val
    return None


def _infer_qty(trade: Dict[str, Any]) -> Optional[float]:
    """Infer filled quantity."""
    for key in ("filled_qty", "qty"):
        if key in trade:
            val = _to_float(trade.get(key))
            if val is not None:
                return val
    return None


def _infer_pre_post_prices(trade: Dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
    """
    Try to get pre- and post-trade prices from stored fields.

    In a more advanced setup these could be computed from historical quotes
    around `created_at`, but here we rely on optional columns:
      - pre_trade_price
      - post_trade_price
    """
    pre = _to_float(trade.get("pre_trade_price"))
    post = _to_float(trade.get("post_trade_price"))
    return pre, post


def _compute_implementation_shortfall(
    side_sign: int,
    arrival_price: Optional[float],
    fill_price: Optional[float],
    qty: Optional[float],
) -> Optional[float]:
    if side_sign == 0 or arrival_price is None or fill_price is None or qty is None:
        return None
    return (arrival_price - fill_price) * qty * side_sign


def _compute_market_impact(
    side_sign: int,
    pre_price: Optional[float],
    post_price: Optional[float],
    qty: Optional[float],
) -> Optional[float]:
    if side_sign == 0 or pre_price is None or post_price is None or qty is None:
        return None
    return (post_price - pre_price) * qty * side_sign


def _compute_opportunity_cost(
    trade: Dict[str, Any],
    side_sign: int,
    limit_price: Optional[float],
    qty: Optional[float],
) -> Optional[float]:
    """
    Estimate opportunity cost for unfilled or partially filled limit orders.

    Simple heuristic:
      - If status == 'filled' -> 0
      - If status != 'filled' and limit_price is set, we compare to:
            - best_price_after: post_trade_price (if available)
        For a buy limit:
            if best_price_after > limit_price, cost = (best_price_after - limit_price) * qty
        For a sell limit:
            if best_price_after < limit_price, cost = (limit_price - best_price_after) * qty
    """
    status = (trade.get("status") or "").lower()
    if status in {"filled", "closed"}:
        return 0.0
    if side_sign == 0 or limit_price is None or qty is None:
        return None

    _, post_price = _infer_pre_post_prices(trade)
    if post_price is None:
        return None

    if side_sign > 0:
        # Buy limit: missed upside
        if post_price > limit_price:
            return (post_price - limit_price) * qty
        return 0.0
    else:
        # Sell limit: missed downside protection
        if post_price < limit_price:
            return (limit_price - post_price) * qty
        return 0.0


def _insert_tca_row(row: Dict[str, Any]) -> None:
    """Insert a TCA result row into Supabase tca_log."""
    client = _get_supabase_client()
    client.table("tca_log").insert(row).execute()


def analyze_trade(trade_id: str) -> Dict[str, Any]:
    """
    Run TCA for a single trade and store the result in Supabase tca_log.

    Returns a dict with computed metrics, e.g.:
      {
        "trade_id": ...,
        "symbol": ...,
        "side": ...,
        "qty": ...,
        "arrival_price": ...,
        "fill_price": ...,
        "implementation_shortfall": ...,
        "market_impact": ...,
        "opportunity_cost": ...,
        "created_at": ...,
      }
    """
    trade = _fetch_trade(trade_id)

    symbol = trade.get("symbol")
    side = trade.get("side")
    side_sign = _side_sign(side)
    qty = _infer_qty(trade)
    arrival_price = _infer_arrival_price(trade)
    fill_price = _infer_fill_price(trade)
    limit_price = _to_float(trade.get("limit_price"))
    pre_price, post_price = _infer_pre_post_prices(trade)

    impl_shortfall = _compute_implementation_shortfall(side_sign, arrival_price, fill_price, qty)
    market_impact = _compute_market_impact(side_sign, pre_price, post_price, qty)
    opp_cost = _compute_opportunity_cost(trade, side_sign, limit_price, qty)

    created_at = trade.get("created_at")
    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()

    result: Dict[str, Any] = {
        "trade_id": trade_id,
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "arrival_price": arrival_price,
        "fill_price": fill_price,
        "limit_price": limit_price,
        "pre_trade_price": pre_price,
        "post_trade_price": post_price,
        "implementation_shortfall": impl_shortfall,
        "market_impact": market_impact,
        "opportunity_cost": opp_cost,
        "status": trade.get("status"),
        "created_at": created_at,
    }

    _insert_tca_row(result)
    return result


def analyze_weekly_tca(
    week_start: datetime,
    week_end: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Aggregate weekly TCA metrics from tca_log between week_start and week_end.

    Returns:
      {
        "from": iso,
        "to": iso,
        "avg_slippage": ...,
        "avg_market_impact": ...,
        "avg_opportunity_cost": ...,
        "best_trade_id": ...,
        "worst_trade_id": ...,
        "num_trades": ...,
      }
    """
    client = _get_supabase_client()
    if week_end is None:
        week_end = week_start + timedelta(days=7)

    start_iso = week_start.replace(tzinfo=timezone.utc).isoformat()
    end_iso = week_end.replace(tzinfo=timezone.utc).isoformat()

    resp = (
        client.table("tca_log")
        .select("*")
        .gte("created_at", start_iso)
        .lt("created_at", end_iso)
        .execute()
    )
    rows = getattr(resp, "data", None) or resp.data  # type: ignore[attr-defined]

    if not rows:
        return {
            "from": start_iso,
            "to": end_iso,
            "avg_slippage": None,
            "avg_market_impact": None,
            "avg_opportunity_cost": None,
            "best_trade_id": None,
            "worst_trade_id": None,
            "num_trades": 0,
        }

    def _acc(name: str) -> list[float]:
        out: list[float] = []
        for r in rows:
            v = _to_float(r.get(name))
            if v is not None:
                out.append(v)
        return out

    slippages = _acc("implementation_shortfall")
    impacts = _acc("market_impact")
    opps = _acc("opportunity_cost")

    def _avg(xs: list[float]) -> Optional[float]:
        return sum(xs) / len(xs) if xs else None

    # Best/worst executions by implementation shortfall (higher is better for positive PnL)
    best_trade_id = None
    worst_trade_id = None
    if slippages:
        # Map trade_id -> shortfall
        by_id = {
            r["trade_id"]: _to_float(r.get("implementation_shortfall"), 0.0) or 0.0
            for r in rows
            if r.get("trade_id") is not None
        }
        if by_id:
            best_trade_id = max(by_id, key=by_id.get)
            worst_trade_id = min(by_id, key=by_id.get)

    return {
        "from": start_iso,
        "to": end_iso,
        "avg_slippage": _avg(slippages),
        "avg_market_impact": _avg(impacts),
        "avg_opportunity_cost": _avg(opps),
        "best_trade_id": best_trade_id,
        "worst_trade_id": worst_trade_id,
        "num_trades": len(rows),
    }

