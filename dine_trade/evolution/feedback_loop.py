"""Feedback loop: vector DB memory for self-improving signals (Phase 14.5).

After each trade closes:
  - Embed the decision context (agent reasoning + market state) with outcome (PnL).
  - vector_db.upsert_trade_memory(trade_id, reasoning_text, pnl, regime, symbol)

Before each new trade:
  - Query for similar past situations.
  - If historical analogues had negative average PnL → downweight the signal.
  - If historical analogues had positive average PnL → upweight the signal.

This creates a self-improving system where past mistakes reduce future risk.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Multiplier = 1 + k * avg_pnl; clamp to [0.5, 1.5]. e.g. avg -3 → ~0.88, avg +5 → 1.2
FEEDBACK_PNL_SENSITIVITY = 0.04
FEEDBACK_MULTIPLIER_MIN = 0.5
FEEDBACK_MULTIPLIER_MAX = 1.5


def _reasoning_text_from_context(
    agent_verdicts: Dict[str, Any],
    market_regime: str,
    macro_snapshot: Dict[str, Any],
    technical_snapshot: Dict[str, Any],
    sentiment_score: Optional[float],
    symbol: str,
) -> str:
    """Build a single text block from decision context for embedding."""
    parts: List[str] = [f"Symbol: {symbol}. Market regime: {market_regime or 'unknown'}."]
    if macro_snapshot:
        parts.append(f"Macro: {macro_snapshot}.")
    if technical_snapshot:
        parts.append(f"Technicals: {technical_snapshot}.")
    if sentiment_score is not None:
        parts.append(f"Sentiment score: {sentiment_score}.")
    for agent_name, data in (agent_verdicts or {}).items():
        if isinstance(data, dict):
            verdict = data.get("verdict", "")
            score = data.get("score", "")
            reasoning = (data.get("reasoning") or "")[:300]
            parts.append(f"{agent_name}: {verdict} score={score}. {reasoning}")
    return " ".join(parts)


def record_trade_to_memory(
    trade_id: str,
    reasoning_text: str,
    pnl: float,
    regime: str,
    symbol: str,
    *,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    After a trade closes: store decision context + outcome in vector DB.

    Safe to call even if Pinecone is not configured; logs and returns without raising.
    """
    try:
        from dine_trade.storage.vector_db import upsert_trade_memory
        upsert_trade_memory(
            trade_id=trade_id,
            reasoning_text=reasoning_text,
            pnl=pnl,
            regime=regime or "unknown",
            symbol=symbol,
            extra_metadata=extra_metadata,
        )
    except Exception as e:
        logger.warning("Failed to upsert trade memory to vector DB: %s", e)


def record_trade_outcome_to_memory(
    trade_id: str,
    symbol: str,
    pnl: float,
    *,
    agent_verdicts: Optional[Dict[str, Any]] = None,
    market_regime: Optional[str] = None,
    macro_snapshot: Optional[Dict[str, Any]] = None,
    technical_snapshot: Optional[Dict[str, Any]] = None,
    sentiment_score: Optional[float] = None,
    side: Optional[str] = None,
    asset_class: Optional[str] = None,
) -> None:
    """
    One-shot: build reasoning text from context and upsert to vector DB.

    Call this after each trade close (e.g. from performance_tracker or executor).
    """
    reasoning_text = _reasoning_text_from_context(
        agent_verdicts or {},
        market_regime or "unknown",
        macro_snapshot or {},
        technical_snapshot or {},
        sentiment_score,
        symbol,
    )
    extra: Dict[str, Any] = {}
    if side:
        extra["side"] = str(side)
    if asset_class:
        extra["asset_class"] = str(asset_class)
    record_trade_to_memory(
        trade_id=trade_id,
        reasoning_text=reasoning_text,
        pnl=pnl,
        regime=market_regime or "unknown",
        symbol=symbol,
        extra_metadata=extra or None,
    )


def get_similar_trade_outcomes(
    reasoning_text: str,
    symbol: Optional[str] = None,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    """
    Before a new trade: query similar past situations and their outcomes.

    Returns list of dicts with id, score, metadata (metadata contains pnl, regime, symbol).
    """
    try:
        from dine_trade.storage.vector_db import query_similar_trades
        return query_similar_trades(reasoning_text, symbol=symbol, top_k=top_k)
    except Exception as e:
        logger.warning("Failed to query similar trades from vector DB: %s", e)
        return []


def _average_pnl_from_matches(matches: List[Dict[str, Any]]) -> Optional[float]:
    """Extract PnL from metadata and return average. None if no valid pnl."""
    pnls: List[float] = []
    for m in matches:
        meta = m.get("metadata") or {}
        p = meta.get("pnl")
        if p is None:
            continue
        try:
            pnls.append(float(p))
        except (TypeError, ValueError):
            continue
    if not pnls:
        return None
    return sum(pnls) / len(pnls)


def get_feedback_weight(
    reasoning_text: str,
    symbol: Optional[str] = None,
    top_k: int = 10,
    *,
    pnl_sensitivity: float = FEEDBACK_PNL_SENSITIVITY,
    multiplier_min: float = FEEDBACK_MULTIPLIER_MIN,
    multiplier_max: float = FEEDBACK_MULTIPLIER_MAX,
) -> float:
    """
    Before a new trade: compute a signal multiplier from similar past outcomes.

    - If historical analogues had negative average PnL → returns < 1.0 (downweight).
    - If historical analogues had positive average PnL → returns > 1.0 (upweight).
    - If no similar trades or vector DB unavailable → returns 1.0 (neutral).

    Example: avg PnL -3 → ~0.88; avg PnL +5 → 1.2 (with default sensitivity).
    """
    matches = get_similar_trade_outcomes(reasoning_text, symbol=symbol, top_k=top_k)
    avg_pnl = _average_pnl_from_matches(matches)
    if avg_pnl is None:
        return 1.0
    mult = 1.0 + pnl_sensitivity * avg_pnl
    if mult < multiplier_min:
        mult = multiplier_min
    if mult > multiplier_max:
        mult = multiplier_max
    return round(mult, 4)
