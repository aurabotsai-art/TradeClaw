"""Universe Expansion Agent: scoring and ranking new symbols for inclusion.

Responsibilities:
  - Periodically scan equities/crypto/forex universes for new alpha opportunities.
  - score_universe_candidate(symbol) -> float:
        * Runs Researcher + Chartist agents on the candidate.
        * Checks liquidity (avg daily dollar volume > $10M where applicable).
        * Checks correlation to existing positions/universe (< 0.7).
  - Persist scored candidates into Supabase `universe_candidates` table.
  - Provide helper to suggest monthly universe changes (add top 3 candidates,
    remove bottom 3 performers) based on recent trade_outcomes.

Notes:
  - This agent is designed for offline / batch jobs (e.g. monthly).
  - It uses live data connectors and Gemini agents, so it should not be called
    at very high frequency.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from dine_trade.config.settings import UNIVERSE_DEFAULT
from dine_trade.data.providers import get_ohlcv_with_failover
from dine_trade.agents.researcher.agent import run_researcher
from dine_trade.agents.chartist.agent import run_chartist
from dine_trade.risk.correlation_limits import compute_correlation_matrix, _infer_asset_type  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)


LiquidityCheck = Tuple[bool, float | None]


@dataclass
class CandidateScore:
    symbol: str
    asset_class: str
    score: float
    researcher_score: float
    chartist_score: float
    liquidity_ok: bool
    avg_dollar_volume: float | None
    max_corr_to_universe: float | None
    components: Dict[str, Any]


def _asset_class_from_symbol(symbol: str) -> str:
    """Infer high-level asset class from symbol."""
    s = symbol.upper()
    if "_" in s:
        return "FOREX"
    if s.endswith("USDT"):
        return "CRYPTO"
    return "EQUITY"


def _check_liquidity(ohlcv_df: pd.DataFrame, *, window: int = 30) -> LiquidityCheck:
    """Return (liquidity_ok, avg_dollar_volume) for the last `window` bars."""
    if ohlcv_df is None or getattr(ohlcv_df, "empty", True):
        return False, None
    df = ohlcv_df.copy()
    if "close" not in df.columns or "volume" not in df.columns:
        # Some FX feeds lack volume; treat as unknown but not fatal.
        return True, None
    tail = df.tail(window)
    try:
        dollar_vol = (tail["close"].astype(float) * tail["volume"].astype(float)).mean()
        if pd.isna(dollar_vol):
            return False, None
        return bool(dollar_vol >= 10_000_000.0), float(dollar_vol)
    except Exception:  # pragma: no cover
        return False, None


def _max_corr_with_universe(symbol: str, existing_universe: Sequence[str]) -> float | None:
    """Compute max |correlation| between symbol and existing universe (30d returns)."""
    symbols = list({sym.upper() for sym in existing_universe} | {symbol.upper()})
    if len(symbols) < 2:
        return None

    # Build minimal positions dict for correlation_limits API
    positions = {
        sym: {"symbol": sym, "asset_type": _infer_asset_type(sym), "notional": 1.0}
        for sym in symbols
    }
    corr = compute_correlation_matrix(positions)
    if corr.empty or symbol.upper() not in corr.columns:
        return None

    row = corr.loc[symbol.upper()]
    # Exclude self-correlation
    others = [abs(float(v)) for idx, v in row.items() if idx != symbol.upper() and not pd.isna(v)]
    return max(others) if others else None


def _normalize_agent_score(agent_res: Dict[str, Any]) -> float:
    """Map agent score/verdict to 0..1."""
    if not isinstance(agent_res, dict):
        return 0.0
    verdict = str(agent_res.get("verdict", "")).upper()
    raw = agent_res.get("score", 0.0)
    try:
        s = float(raw)
    except (TypeError, ValueError):
        s = 0.0
    s = max(0.0, min(10.0, s))
    base = s / 10.0
    if verdict == "REJECT":
        # Penalize rejects, but keep some gradation
        return base * 0.3
    return base


def score_universe_candidate_detailed(
    symbol: str,
    *,
    existing_universe: Optional[Sequence[str]] = None,
    ohlcv_days: int = 120,
    min_corr_threshold: float = 0.7,
) -> CandidateScore:
    """Score a single symbol as a universe candidate.

    Steps:
      - Load recent OHLCV.
      - Run Researcher (fundamental) and Chartist (technical) agents.
      - Check liquidity (avg dollar volume > $10M where volume data exists).
      - Check max |correlation| to existing_universe (< 0.7 preferred).
      - Combine into a 0..1 score; illiquid or highly correlated names receive
        low/zero scores.
    """
    asset_class = _asset_class_from_symbol(symbol)
    universe = list(existing_universe or UNIVERSE_DEFAULT)

    try:
        ohlcv_df = get_ohlcv_with_failover(symbol, days=ohlcv_days)
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to load OHLCV for %s in universe scanner: %s", symbol, e)
        raise

    if ohlcv_df is None or getattr(ohlcv_df, "empty", True):
        raise ValueError(f"No OHLCV data for candidate {symbol}")

    # Liquidity filter (equity/crypto); FX may not have reliable volume
    liquidity_ok, avg_dollar_vol = _check_liquidity(ohlcv_df)

    # Agents
    fundamentals = {}  # hook for future fundamentals integration
    sec_context = None
    researcher_res = run_researcher(
        symbol=symbol,
        ohlcv_df=ohlcv_df,
        fundamentals=fundamentals if asset_class == "EQUITY" else None,
        sec_context=sec_context if asset_class == "EQUITY" else None,
    )
    chartist_res = run_chartist(symbol=symbol, ohlcv_df=ohlcv_df)

    r_score = _normalize_agent_score(researcher_res)
    c_score = _normalize_agent_score(chartist_res)

    # Correlation to existing universe
    try:
        max_corr = _max_corr_with_universe(symbol, universe)
    except Exception as e:  # pragma: no cover
        logger.warning("Correlation check failed for %s: %s", symbol, e)
        max_corr = None

    corr_penalty = 1.0
    if max_corr is not None and max_corr >= min_corr_threshold:
        corr_penalty = 0.0

    # Combine into final 0..1 score
    base_agent_score = 0.5 * r_score + 0.5 * c_score

    liq_multiplier = 1.0 if liquidity_ok else 0.0
    final_score = float(base_agent_score * liq_multiplier * corr_penalty)

    components = {
        "researcher": researcher_res,
        "chartist": chartist_res,
        "base_agent_score": base_agent_score,
        "liquidity_ok": liquidity_ok,
        "avg_dollar_volume": avg_dollar_vol,
        "max_corr_to_universe": max_corr,
        "min_corr_threshold": min_corr_threshold,
        "asset_class": asset_class,
    }

    return CandidateScore(
        symbol=symbol,
        asset_class=asset_class,
        score=round(final_score, 4),
        researcher_score=r_score,
        chartist_score=c_score,
        liquidity_ok=liquidity_ok,
        avg_dollar_volume=avg_dollar_vol,
        max_corr_to_universe=max_corr,
        components=components,
    )


def score_universe_candidate(symbol: str) -> float:
    """Public helper: simple float score for a candidate symbol."""
    detailed = score_universe_candidate_detailed(symbol)
    return detailed.score


def scan_universe_candidates(
    symbols: Iterable[str],
    *,
    existing_universe: Optional[Sequence[str]] = None,
) -> List[CandidateScore]:
    """Score a batch of symbols and persist them as candidates in Supabase.

    Caller is expected to pass an appropriate symbol list:
      - S&P 500 constituents for equities.
      - A curated crypto list for momentum/volume screen.
      - A set of FX pairs of interest.
    """
    from dine_trade.storage.supabase_client import insert_universe_candidate  # local import

    existing = list(existing_universe or UNIVERSE_DEFAULT)
    results: List[CandidateScore] = []
    scanned_at = datetime.now(timezone.utc).isoformat()

    for sym in symbols:
        try:
            cs = score_universe_candidate_detailed(sym, existing_universe=existing)
        except Exception as e:  # pragma: no cover
            logger.warning("Failed to score universe candidate %s: %s", sym, e)
            continue

        results.append(cs)
        row = {
            "symbol": cs.symbol,
            "asset_class": cs.asset_class,
            "score": cs.score,
            "components": cs.components,
            "scanned_at": scanned_at,
        }
        try:
            insert_universe_candidate(row)
        except Exception as e:  # pragma: no cover
            logger.warning("Failed to persist universe candidate %s: %s", sym, e)

    return results


def suggest_universe_changes(
    *,
    current_universe: Optional[Sequence[str]] = None,
    lookback_days: int = 180,
    top_k: int = 3,
) -> Dict[str, List[str]]:
    """Suggest adds/removals for monthly universe review.

    - Adds: top `top_k` highest-scoring candidates from `universe_candidates`
      not already in current_universe.
    - Removes: bottom `top_k` performers from trade_outcomes PnL over
      `lookback_days` among current_universe members.

    This function does not mutate any live config; it only suggests changes.
    """
    from dine_trade.storage.supabase_client import (  # local import
        select_trade_outcomes_since,
        select_universe_candidates,
    )

    universe = list(current_universe or UNIVERSE_DEFAULT)

    # 1) Additions: top scoring recent candidates, excluding already-in-universe
    candidates = select_universe_candidates(limit=500)
    add_candidates: List[str] = []
    seen: set[str] = set()
    for row in sorted(candidates, key=lambda r: float(r.get("score", 0.0) or 0.0), reverse=True):
        sym = str(row.get("symbol", "")).upper()
        if not sym or sym in universe or sym in seen:
            continue
        seen.add(sym)
        add_candidates.append(sym)
        if len(add_candidates) >= top_k:
            break

    # 2) Removals: worst PnL symbols from trade_outcomes over lookback window
    outcomes = select_trade_outcomes_since(lookback_days)
    pnl_by_symbol: Dict[str, float] = {}
    for o in outcomes:
        sym = str(o.get("symbol", "")).upper()
        if sym not in universe:
            continue
        try:
            p = float(o.get("pnl", 0.0) or 0.0)
        except (TypeError, ValueError):
            p = 0.0
        pnl_by_symbol[sym] = pnl_by_symbol.get(sym, 0.0) + p

    remove_candidates: List[str] = []
    if pnl_by_symbol:
        sorted_syms = sorted(pnl_by_symbol.items(), key=lambda kv: kv[1])  # ascending PnL
        remove_candidates = [sym for sym, _ in sorted_syms[:top_k]]

    return {
        "add": add_candidates,
        "remove": remove_candidates,
    }

