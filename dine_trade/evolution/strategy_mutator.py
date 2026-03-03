"""Agent weight optimization by Information Coefficient.

Currently consensus requires ALL 3 agents to APPROVE. This module optimizes by
weighting agents by their recent IC (Information Coefficient) over the last 60 days:
- Compute each agent's IC (correlation of score with trade PnL).
- Rebalance weights proportionally to IC with a 10% min floor.
- Consensus can use weighted score threshold (CONSENSUS_THRESHOLD = 0.7) instead
  of all-three-approve.

Intended to run monthly; caller passes performance_data from trade_outcomes (e.g.
last 60 days).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Weighted consensus: approved when weighted score >= this threshold (0–1 scale)
CONSENSUS_THRESHOLD = 0.7

# No agent may go below this weight so they are never fully ignored
MIN_AGENT_WEIGHT = 0.10

# Specialist agents that are weighted by IC (risk_officer stays separate)
SPECIALIST_AGENTS = ("researcher", "sentiment", "chartist")

# Default equal weights when no performance data or rebalance not yet run
AGENT_WEIGHTS_DEFAULT: Dict[str, float] = {
    "researcher": 1.0 / 3,
    "sentiment": 1.0 / 3,
    "chartist": 1.0 / 3,
}

# Module-level current weights (updated by rebalance_agent_weights)
_agent_weights: Dict[str, float] = dict(AGENT_WEIGHTS_DEFAULT)


def _pearson_ic(scores: List[float], outcomes: List[float]) -> float:
    """Information Coefficient: Pearson correlation between agent scores and trade outcomes (PnL)."""
    n = len(scores)
    if n != len(outcomes) or n < 2:
        return 0.0
    mean_s = sum(scores) / n
    mean_o = sum(outcomes) / n
    cov = sum((s - mean_s) * (o - mean_o) for s, o in zip(scores, outcomes)) / n
    var_s = sum((s - mean_s) ** 2 for s in scores) / n
    var_o = sum((o - mean_o) ** 2 for o in outcomes) / n
    if var_s <= 0 or var_o <= 0:
        return 0.0
    r = cov / (var_s ** 0.5 * var_o ** 0.5)
    return max(-1.0, min(1.0, r))


def _score_from_verdict(agent_entry: Any) -> float:
    """Normalize agent verdict to a 0–1 score for IC. APPROVE + score 8 -> 0.8."""
    if not isinstance(agent_entry, dict):
        return 0.5
    verdict = (agent_entry.get("verdict") or "").upper()
    raw = agent_entry.get("score")
    try:
        s = float(raw) if raw is not None else 0.0
    except (TypeError, ValueError):
        s = 0.0
    # Map to 0–1: score typically 0–10, or 0/1 for verdict-only
    if verdict == "REJECT":
        return 0.0
    if s <= 0:
        return 0.5 if verdict == "APPROVE" else 0.0
    return min(1.0, s / 10.0)


def _extract_scores_and_pnls(
    performance_data: List[Dict[str, Any]],
) -> Dict[str, tuple[List[float], List[float]]]:
    """For each specialist agent, return (scores, pnls) lists from performance_data."""
    by_agent: Dict[str, tuple[List[float], List[float]]] = {
        a: ([], []) for a in SPECIALIST_AGENTS
    }
    for row in performance_data:
        try:
            pnl = float(row.get("pnl", 0))
        except (TypeError, ValueError):
            pnl = 0.0
        verdicts = row.get("agent_verdicts") or {}
        for agent in SPECIALIST_AGENTS:
            entry = verdicts.get(agent)
            score = _score_from_verdict(entry)
            by_agent[agent][0].append(score)
            by_agent[agent][1].append(pnl)
    return by_agent


def compute_agent_ics(performance_data: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute Information Coefficient for each specialist over the given outcomes."""
    by_agent = _extract_scores_and_pnls(performance_data)
    ics: Dict[str, float] = {}
    for agent in SPECIALIST_AGENTS:
        scores, pnls = by_agent[agent]
        ic = _pearson_ic(scores, pnls) if len(scores) >= 2 else 0.0
        ics[agent] = round(ic, 4)
    return ics


def rebalance_agent_weights(performance_data: List[Dict[str, Any]]) -> Dict[str, float]:
    """Rebalance agent weights by IC over recent outcomes (e.g. last 60 days).

    Run monthly. Computes each agent's IC, sets weights proportionally to IC,
    applies a 10% min floor, then normalizes. Updates module-level weights and
    returns the new weight dict.
    """
    global _agent_weights
    ics = compute_agent_ics(performance_data)
    total_ic = sum(max(ic, 0.0) for ic in ics.values())
    if total_ic <= 0:
        # No predictive signal or no data: use equal weights with floor
        raw = {a: 1.0 for a in SPECIALIST_AGENTS}
    else:
        raw = {a: max(ics.get(a, 0.0), 0.0) for a in SPECIALIST_AGENTS}
    # Apply floor
    floored = {a: max(raw[a], MIN_AGENT_WEIGHT) for a in SPECIALIST_AGENTS}
    s = sum(floored.values())
    if s <= 0:
        _agent_weights = dict(AGENT_WEIGHTS_DEFAULT)
        return dict(_agent_weights)
    weights = {a: round(floored[a] / s, 4) for a in SPECIALIST_AGENTS}
    _agent_weights = weights
    logger.info("Agent weights rebalanced from IC (60d): %s", weights)
    return dict(weights)


def get_agent_weights() -> Dict[str, float]:
    """Return current agent weights (from last rebalance or default)."""
    return dict(_agent_weights)


def weighted_consensus_score(agent_results: Dict[str, Any], weights: Dict[str, float] | None = None) -> float:
    """Compute weighted consensus score (0–1) from agent_results.

    Each specialist contributes (score 0–1) * weight; risk_officer is not weighted
    by IC but can be required separately. Returns weighted sum of specialist scores.
    """
    w = weights or get_agent_weights()
    total = 0.0
    for agent in SPECIALIST_AGENTS:
        entry = (agent_results or {}).get(agent)
        s = _score_from_verdict(entry)
        total += s * w.get(agent, 1.0 / 3)
    return round(total, 4)


def is_approved_weighted(
    agent_results: Dict[str, Any],
    *,
    threshold: float = CONSENSUS_THRESHOLD,
    weights: Dict[str, float] | None = None,
    risk_officer_required: bool = True,
) -> bool:
    """True if weighted consensus score >= threshold and (optionally) risk_officer APPROVE."""
    score = weighted_consensus_score(agent_results, weights=weights)
    if score < threshold:
        return False
    if not risk_officer_required:
        return True
    ro = (agent_results or {}).get("risk_officer") or {}
    return (ro.get("verdict") or "").upper() == "APPROVE"


def rebalance_weights_from_supabase(lookback_days: int = 60) -> Dict[str, float]:
    """Fetch trade outcomes from Supabase (last lookback_days) and rebalance weights.

    Convenience for monthly job: pulls performance data and calls rebalance_agent_weights.
    """
    try:
        from dine_trade.storage.supabase_client import select_trade_outcomes_since
        performance_data = select_trade_outcomes_since(lookback_days)
    except Exception as e:
        logger.warning("Could not fetch trade outcomes for weight rebalance: %s", e)
        return get_agent_weights()
    return rebalance_agent_weights(performance_data)
