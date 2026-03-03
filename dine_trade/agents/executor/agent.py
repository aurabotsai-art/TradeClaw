"""Executor Agent.

Inputs:
    - consensus: dict with at least {"approved": bool, "suggested_qty": float, "symbol": str}
    - price_a: float (e.g. OHLCV-derived price)
    - price_b: float (e.g. live quote mid)
    - account_equity: float
    - optional kwargs passed through to Risk Officer (e.g. volatility, daily_drawdown_pct, win_rate, avg_win, avg_loss)

Flow:
    1) If consensus not approved -> no order; return.
    2) DataValidator.validate_price_agreement(price_a, price_b, 0.1) before order; if invalid, abort.
    3) Re-check Risk Officer immediately before sending order.
       - Cap quantity by Risk's max_qty.
    4) If still approved -> smart_limit_order(symbol, "buy", qty, 60).

Return:
    {
        "order_id": str | None,
        "status": str,   # e.g. "SKIPPED", "ABORTED", "RISK_REJECT", "SUBMITTED"
        "symbol": str,
        "qty": float,
        "reason": str,
        "raw_order": dict | None,
    }
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from dine_trade.agents.risk_officer import run_risk_officer
from dine_trade.execution.alpaca_client import smart_limit_order
from dine_trade.utils import validate_price_agreement

logger = logging.getLogger(__name__)


def run_executor(
    consensus: Dict[str, Any],
    *,
    price_a: float,
    price_b: float,
    account_equity: float,
    volatility: Optional[float] = None,
    daily_drawdown_pct: Optional[float] = None,
    win_rate: Optional[float] = None,
    avg_win: Optional[float] = None,
    avg_loss: Optional[float] = None,
) -> Dict[str, Any]:
    """Execute a trade if consensus and risk checks pass.

    This is designed to be called after async consensus orchestration.
    """
    symbol = str(consensus.get("symbol") or "")
    approved = bool(consensus.get("approved", False))
    suggested_qty = float(consensus.get("suggested_qty", 0.0) or 0.0)

    base_result: Dict[str, Any] = {
        "order_id": None,
        "status": "SKIPPED",
        "symbol": symbol,
        "qty": 0.0,
        "reason": "",
        "raw_order": None,
    }

    if not symbol:
        base_result["reason"] = "Missing symbol in consensus."
        return base_result

    if not approved or suggested_qty <= 0:
        base_result["reason"] = "Consensus not approved or non-positive suggested_qty; no order."
        return base_result

    # 1) DataValidator: price sanity check before any order
    valid, msg = validate_price_agreement(price_a, price_b, tolerance_pct=0.1)
    if not valid:
        logger.warning("DataValidator failed for %s: %s; aborting order", symbol, msg)
        base_result["status"] = "ABORTED"
        base_result["reason"] = f"DataValidator failed: {msg}"
        return base_result

    # Use price_b (e.g. live quote mid) as execution reference price
    exec_price = float(price_b)
    if exec_price <= 0:
        base_result["status"] = "ABORTED"
        base_result["reason"] = "Execution price must be positive."
        return base_result

    # 2) Re-check Risk Officer immediately before order
    risk_res = run_risk_officer(
        symbol=symbol,
        price=exec_price,
        account_equity=account_equity,
        qty=suggested_qty,
        volatility=volatility,
        daily_drawdown_pct=daily_drawdown_pct,
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
    )

    risk_verdict = str(risk_res.get("verdict", "")).upper()
    max_qty = float(risk_res.get("max_qty", 0.0) or 0.0)

    if risk_verdict != "APPROVE" or max_qty <= 0:
        base_result["status"] = "RISK_REJECT"
        base_result["reason"] = f"Risk Officer veto: {risk_res.get('reasoning', '')}"
        base_result["qty"] = 0.0
        return base_result

    qty = min(suggested_qty, max_qty)
    if qty <= 0:
        base_result["status"] = "RISK_REJECT"
        base_result["reason"] = "Capped quantity is non-positive after Risk Officer check."
        return base_result

    # 3) smart_limit_order using capped qty
    order = smart_limit_order(symbol=symbol, side="buy", qty=qty, time_in_force_sec=60)
    order_id = order.get("id")
    status = order.get("status") or "SUBMITTED"

    return {
        "order_id": order_id,
        "status": status,
        "symbol": symbol,
        "qty": qty,
        "reason": f"Order submitted via smart_limit_order at risk-checked size (<= {max_qty:.4f}).",
        "raw_order": order,
        "risk_result": risk_res,
        "data_validator": {"price_a": price_a, "price_b": price_b},
    }

