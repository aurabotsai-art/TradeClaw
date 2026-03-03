"""Async consensus orchestration for Researcher, Sentiment, Chartist, then Risk Officer.

Audit: asyncio.gather(researcher_task(), sentiment_task(), chartist_task()).

Public API:
    async def run_consensus(
        symbol: str,
        account_equity: float,
        positions: list[dict] | None,
        ohlcv_df,
        headlines,
        *,
        score_threshold: float = 7.0,
        price: float | None = None,
        volatility: float | None = None,
        position_size_usd: float | None = None,
        qty: float | None = None,
    ) -> dict

Return shape:
    {
        "approved": bool,
        "reason": str,
        "suggested_qty": float,
        "agent_results": {
            "researcher": {...},
            "sentiment": {...},
            "chartist": {...},
            "risk_officer": {...},
        },
    }
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


def _normalize_asset_class(asset_class: str | None) -> str:
    """Normalize asset class string."""
    if not asset_class:
        return "EQUITY"
    ac = asset_class.upper()
    if ac not in {"EQUITY", "CRYPTO", "FOREX"}:
        return "EQUITY"
    return ac


def _is_forex_session_open(now: datetime | None = None) -> bool:
    """Return True if we are within Sun 5pm – Fri 5pm EST FOREX session."""
    if now is None:
        now = datetime.now(ZoneInfo("America/New_York"))
    weekday = now.weekday()  # Monday=0, Sunday=6
    hour = now.hour
    minute = now.minute

    # Saturday: closed all day
    if weekday == 5:
        return False
    # Sunday: open from 17:00 onwards
    if weekday == 6:
        return (hour, minute) >= (17, 0)
    # Friday: closed from 17:00 onwards
    if weekday == 4 and (hour, minute) >= (17, 0):
        return False
    # Monday–Thursday: open all day
    return True


async def _load_ohlcv_for_asset_class(symbol: str, asset_class: str, ohlcv_df):
    """If ohlcv_df is empty/None, fetch using the appropriate connector for the asset class."""
    if ohlcv_df is not None and not getattr(ohlcv_df, "empty", True):
        return ohlcv_df

    ac = _normalize_asset_class(asset_class)

    try:
        if ac == "EQUITY":
            from dine_trade.data.providers import get_ohlcv_with_failover

            return await asyncio.to_thread(get_ohlcv_with_failover, symbol, 100)
        if ac == "CRYPTO":
            from dine_trade.data.connectors import binance_connector

            # 1h candles, 200 bars by default
            return await asyncio.to_thread(binance_connector.get_ohlcv, symbol, "1h", 200)
        if ac == "FOREX":
            from dine_trade.data.connectors import oanda_connector

            # H1 granularity, 200 candles by default
            return await asyncio.to_thread(oanda_connector.get_ohlcv, symbol, "H1", 200)
    except Exception as e:  # pragma: no cover - network/remote errors
        logger.warning("Failed to load OHLCV for %s (%s): %s", symbol, ac, e)

    # Fallback: empty frame; caller will handle
    try:
        import pandas as pd

        return pd.DataFrame()
    except Exception:  # pragma: no cover
        return None


async def _run_researcher(symbol: str, ohlcv_df) -> dict[str, Any]:
    """Run Fundamental Researcher in a worker thread."""
    try:
        from dine_trade.agents.researcher import run_researcher
    except Exception as e:  # pragma: no cover - import wiring issues
        logger.exception("Failed to import Researcher agent: %s", e)
        return {"verdict": "REJECT", "score": 0.0, "reasoning": f"Researcher import failed: {e}"}
    return await asyncio.to_thread(run_researcher, symbol, ohlcv_df)


async def _run_sentiment(symbol: str, headlines) -> dict[str, Any]:
    """Run Sentiment agent in a worker thread."""
    try:
        from dine_trade.agents.sentiment import run_sentiment
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to import Sentiment agent: %s", e)
        return {"verdict": "REJECT", "score": 0.0, "reasoning": f"Sentiment import failed: {e}"}
    return await asyncio.to_thread(run_sentiment, symbol, headlines)


async def _run_chartist(symbol: str, ohlcv_df) -> dict[str, Any]:
    """Run Chartist agent in a worker thread."""
    try:
        from dine_trade.agents.chartist import run_chartist
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to import Chartist agent: %s", e)
        return {"verdict": "REJECT", "score": 0.0, "reasoning": f"Chartist import failed: {e}"}
    return await asyncio.to_thread(run_chartist, symbol, ohlcv_df)


async def run_consensus(
    symbol: str,
    account_equity: float,
    positions: list[dict[str, Any]] | None,
    ohlcv_df,
    headlines,
    *,
    asset_class: str = "EQUITY",
    score_threshold: float = 7.0,
    price: float | None = None,
    volatility: float | None = None,
    position_size_usd: float | None = None,
    qty: float | None = None,
    use_weighted_consensus: bool = False,
    use_feedback_loop: bool = False,
) -> dict[str, Any]:
    """Run Researcher, Sentiment, Chartist in parallel, then Risk Officer, and build consensus.

    asset_class: "EQUITY", "CRYPTO", or "FOREX".
    use_weighted_consensus: if True, use IC-based agent weights and CONSENSUS_THRESHOLD (0.7)
        instead of requiring all three specialists to APPROVE.
    use_feedback_loop: if True, query vector DB for similar past trades and scale suggested_qty
        by feedback weight (past losses -> downweight, past gains -> upweight).
    """
    positions = positions or []

    ac = _normalize_asset_class(asset_class)

    # Market-hours gating: crypto runs 24/7; FOREX has explicit session window.
    if ac == "FOREX" and not _is_forex_session_open():
        reason = "FOREX market closed (trading window Sun 5pm – Fri 5pm EST)."
        logger.info(reason)
        return {
            "approved": False,
            "reason": reason,
            "suggested_qty": 0.0,
            "agent_results": {},
        }

    # Load OHLCV if caller did not provide a usable DataFrame.
    ohlcv_df = await _load_ohlcv_for_asset_class(symbol, ac, ohlcv_df)
    if ohlcv_df is None or getattr(ohlcv_df, "empty", True):
        reason = f"No OHLCV data available for {symbol} (asset_class={ac}); cannot form consensus."
        logger.warning(reason)
        return {
            "approved": False,
            "reason": reason,
            "suggested_qty": 0.0,
            "agent_results": {},
        }

    # Fallback price from OHLCV last close if not provided
    if price is None and ohlcv_df is not None and not getattr(ohlcv_df, "empty", True):
        close_col = "close" if "close" in ohlcv_df.columns else ohlcv_df.columns[-1]
        try:
            price = float(ohlcv_df[close_col].iloc[-1])
        except Exception:  # pragma: no cover
            price = None

    # Parallel specialist agents
    researcher_task = _run_researcher(symbol, ohlcv_df)
    sentiment_task = _run_sentiment(symbol, headlines)
    chartist_task = _run_chartist(symbol, ohlcv_df)

    researcher_res, sentiment_res, chartist_res = await asyncio.gather(
        researcher_task,
        sentiment_task,
        chartist_task,
    )

    agent_results: dict[str, Any] = {
        "researcher": researcher_res,
        "sentiment": sentiment_res,
        "chartist": chartist_res,
    }

    # Consensus of three specialists (or weighted by IC when use_weighted_consensus)
    def _approved(agent_res: dict[str, Any]) -> bool:
        verdict_ok = agent_res.get("verdict", "").upper() == "APPROVE"
        score_val = float(agent_res.get("score", 0.0) or 0.0)
        return verdict_ok and score_val >= score_threshold

    all_specialists_ok = (
        _approved(researcher_res)
        and _approved(sentiment_res)
        and _approved(chartist_res)
    )

    consensus_reason_parts: list[str] = []
    if not _approved(researcher_res):
        consensus_reason_parts.append("Researcher veto or low score")
    if not _approved(sentiment_res):
        consensus_reason_parts.append("Sentiment veto or low score")
    if not _approved(chartist_res):
        consensus_reason_parts.append("Chartist veto or low score")

    # Run Risk Officer after specialists
    try:
        from dine_trade.agents.risk_officer import run_risk_officer
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to import Risk Officer agent: %s", e)
        risk_res: dict[str, Any] = {
            "verdict": "REJECT",
            "max_qty": 0.0,
            "reasoning": f"Risk officer import failed: {e}",
        }
    else:
        # Derive position_size_usd if not provided, using price * qty
        if position_size_usd is None and price is not None and qty is not None:
            try:
                position_size_usd = float(price) * float(qty)
            except Exception:  # pragma: no cover
                position_size_usd = None

        risk_res = await asyncio.to_thread(
            run_risk_officer,
            symbol=symbol,
            price=price,
            account_equity=account_equity,
            position_size_usd=position_size_usd,
            qty=qty,
            volatility=volatility,
        )

    agent_results["risk_officer"] = risk_res

    risk_ok = risk_res.get("verdict", "").upper() == "APPROVE"

    if use_weighted_consensus:
        try:
            from dine_trade.evolution.strategy_mutator import (
                CONSENSUS_THRESHOLD,
                is_approved_weighted,
                weighted_consensus_score,
            )
            weighted_score = weighted_consensus_score(agent_results)
            approved = is_approved_weighted(
                agent_results,
                threshold=CONSENSUS_THRESHOLD,
                risk_officer_required=True,
            )
            if approved:
                reason = f"Weighted consensus score {weighted_score:.2f} >= {CONSENSUS_THRESHOLD} and Risk Officer APPROVE."
            else:
                parts_w = []
                if weighted_score < CONSENSUS_THRESHOLD:
                    parts_w.append(f"Weighted score {weighted_score:.2f} < {CONSENSUS_THRESHOLD}")
                if not risk_ok:
                    parts_w.append("Risk Officer REJECT")
                reason = "; ".join(parts_w)
        except Exception as e:  # pragma: no cover
            logger.warning("Weighted consensus fallback to all-approve: %s", e)
            approved = bool(all_specialists_ok and risk_ok)
            reason = "All agents APPROVE with score >= threshold and Risk Officer APPROVE." if approved else "; ".join(consensus_reason_parts + (["Risk Officer REJECT"] if not risk_ok else []))
    else:
        approved = bool(all_specialists_ok and risk_ok)
        if approved:
            reason = "All agents APPROVE with score >= threshold and Risk Officer APPROVE."
        else:
            parts = list(consensus_reason_parts)
            if not risk_ok:
                parts.append("Risk Officer REJECT")
            reason = "; ".join(parts) if parts else "Consensus not approved for unspecified reasons."

    suggested_qty = float(risk_res.get("max_qty", 0.0) or 0.0) if approved else 0.0

    if approved and use_feedback_loop and suggested_qty > 0:
        try:
            from dine_trade.evolution.feedback_loop import get_feedback_weight
            reasoning_parts = [f"Symbol {symbol}."]
            for name, res in agent_results.items():
                if isinstance(res, dict) and (res.get("reasoning") or res.get("verdict")):
                    reasoning_parts.append(f"{name}: {res.get('verdict', '')} { (res.get('reasoning') or '')[:200]}")
            feedback_weight = get_feedback_weight(" ".join(reasoning_parts), symbol=symbol)
            suggested_qty = suggested_qty * feedback_weight
        except Exception as e:  # pragma: no cover
            logger.warning("Feedback loop weight failed: %s", e)

    return {
        "approved": approved,
        "reason": reason,
        "suggested_qty": suggested_qty,
        "agent_results": agent_results,
    }

