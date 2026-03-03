"""Performance tracker: trade outcomes with full context and strategy metrics.

Tracks every trade outcome with a context snapshot at decision time (agent verdicts,
market regime, macro, technicals, sentiment) and actual outcome (PnL, hold duration,
MFE, MAE). Computes strategy metrics (win rate, Sharpe, max drawdown) overall and
by regime, asset class, and by agent signal. Persists to Supabase trade_outcomes
and strategy_performance tables.

Supabase tables (create if missing):

  trade_outcomes:
    id (uuid, default gen_random_uuid()), symbol (text), side (text), asset_class (text),
    entry_time (timestamptz), exit_time (timestamptz), pnl (numeric), hold_duration_seconds (numeric),
    mfe (numeric), mae (numeric), agent_verdicts (jsonb), market_regime (text),
    macro_snapshot (jsonb), technical_snapshot (jsonb), sentiment_score (numeric), created_at (timestamptz default now())

  strategy_performance:
    id (uuid), lookback_days (int), computed_at (timestamptz), win_rate (numeric), avg_winner (numeric),
    avg_loser (numeric), sharpe (numeric), max_drawdown (numeric), n_trades (int),
    by_regime (jsonb), by_asset_class (jsonb), by_agent (jsonb), created_at (timestamptz default now())
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Context snapshot (at time of trade decision)
# ---------------------------------------------------------------------------

def build_trade_outcome_row(
    symbol: str,
    side: str,
    asset_class: str,
    entry_time: datetime,
    exit_time: datetime,
    pnl: float,
    hold_duration_seconds: float,
    mfe: float,
    mae: float,
    *,
    agent_verdicts: Dict[str, Any] | None = None,
    market_regime: str | None = None,
    macro_snapshot: Dict[str, Any] | None = None,
    technical_snapshot: Dict[str, Any] | None = None,
    sentiment_score: float | None = None,
) -> Dict[str, Any]:
    """Build a trade outcome row for storage.

    agent_verdicts: e.g. {"researcher": {"verdict": "APPROVE", "score": 8, "reasoning": "..."}, ...}
    market_regime: e.g. "trending", "ranging"
    macro_snapshot: e.g. {"fed_rate": 5.25, "vix": 18.5}
    technical_snapshot: e.g. {"rsi": 45, "macd": 0.02, "obi": 0.1}
    """
    return {
        "symbol": str(symbol),
        "side": str(side).lower(),
        "asset_class": (asset_class or "EQUITY").upper(),
        "entry_time": entry_time.isoformat() if hasattr(entry_time, "isoformat") else str(entry_time),
        "exit_time": exit_time.isoformat() if hasattr(exit_time, "isoformat") else str(exit_time),
        "pnl": float(pnl),
        "hold_duration_seconds": float(hold_duration_seconds),
        "mfe": float(mfe),
        "mae": float(mae),
        "agent_verdicts": agent_verdicts or {},
        "market_regime": (market_regime or "unknown").lower(),
        "macro_snapshot": macro_snapshot or {},
        "technical_snapshot": technical_snapshot or {},
        "sentiment_score": float(sentiment_score) if sentiment_score is not None else None,
    }


def record_trade_outcome(
    symbol: str,
    side: str,
    asset_class: str,
    entry_time: datetime,
    exit_time: datetime,
    pnl: float,
    hold_duration_seconds: float,
    mfe: float,
    mae: float,
    *,
    agent_verdicts: Dict[str, Any] | None = None,
    market_regime: str | None = None,
    macro_snapshot: Dict[str, Any] | None = None,
    technical_snapshot: Dict[str, Any] | None = None,
    sentiment_score: float | None = None,
    trade_id: str | None = None,
) -> None:
    """Record a closed trade outcome with full context snapshot; store in Supabase trade_outcomes.

    If trade_id is provided, also stores the decision context + outcome in the vector DB
    (Phase 14.5 feedback loop) so similar situations can be used to up/downweight future signals.
    """
    row = build_trade_outcome_row(
        symbol=symbol,
        side=side,
        asset_class=asset_class,
        entry_time=entry_time,
        exit_time=exit_time,
        pnl=pnl,
        hold_duration_seconds=hold_duration_seconds,
        mfe=mfe,
        mae=mae,
        agent_verdicts=agent_verdicts,
        market_regime=market_regime,
        macro_snapshot=macro_snapshot,
        technical_snapshot=technical_snapshot,
        sentiment_score=sentiment_score,
    )
    try:
        from dine_trade.storage.supabase_client import insert_trade_outcome
        insert_trade_outcome(row)
    except Exception as e:
        logger.warning("Failed to insert trade outcome into Supabase: %s", e)

    if trade_id:
        try:
            from dine_trade.evolution.feedback_loop import record_trade_outcome_to_memory
            record_trade_outcome_to_memory(
                trade_id=trade_id,
                symbol=symbol,
                pnl=pnl,
                agent_verdicts=agent_verdicts,
                market_regime=market_regime,
                macro_snapshot=macro_snapshot,
                technical_snapshot=technical_snapshot,
                sentiment_score=sentiment_score,
                side=side,
                asset_class=asset_class,
            )
        except Exception as e:
            logger.warning("Failed to record trade to vector DB memory: %s", e)


# ---------------------------------------------------------------------------
# Strategy metrics from trade outcomes
# ---------------------------------------------------------------------------

def _metrics_from_pnls(pnls: List[float]) -> Dict[str, Any]:
    """Compute win_rate, avg_winner, avg_loser, sharpe, max_drawdown from list of PnLs."""
    if not pnls:
        return {
            "win_rate": 0.0,
            "avg_winner": 0.0,
            "avg_loser": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "n_trades": 0,
        }
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    n = len(pnls)
    win_rate = len(wins) / n if n else 0.0
    avg_winner = sum(wins) / len(wins) if wins else 0.0
    avg_loser = sum(losses) / len(losses) if losses else 0.0

    mean_pnl = sum(pnls) / n
    variance = sum((p - mean_pnl) ** 2 for p in pnls) / n if n else 0.0
    std_pnl = variance ** 0.5 if variance > 0 else 0.0
    sharpe = (mean_pnl / std_pnl) if std_pnl > 0 else 0.0

    # Max drawdown from cumulative PnL
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        cum += p
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    return {
        "win_rate": round(win_rate, 4),
        "avg_winner": round(avg_winner, 4),
        "avg_loser": round(avg_loser, 4),
        "sharpe": round(sharpe, 4),
        "max_drawdown": round(max_dd, 4),
        "n_trades": n,
    }


def _agent_key_from_verdicts(agent_verdicts: Any) -> str:
    """Which specialist was the 'signal' (e.g. highest score). Returns researcher|sentiment|chartist."""
    if not isinstance(agent_verdicts, dict):
        return "unknown"
    best_agent = None
    best_score = -1.0
    for name in ("researcher", "sentiment", "chartist"):
        entry = agent_verdicts.get(name)
        if isinstance(entry, dict):
            s = entry.get("score")
            try:
                sc = float(s) if s is not None else -1.0
            except (TypeError, ValueError):
                sc = -1.0
            if sc > best_score:
                best_score = sc
                best_agent = name
    return best_agent or "unknown"


def compute_strategy_metrics(lookback_days: int = 30) -> Dict[str, Any]:
    """Compute strategy metrics from trade outcomes in the last lookback_days.

    Returns:
      - win_rate, avg_winner, avg_loser, sharpe, max_drawdown (overall)
      - by_regime: { regime -> same metrics } (e.g. trending vs ranging)
      - by_asset_class: { asset_class -> same metrics } (equities, crypto, forex)
      - by_agent: { agent_name -> same metrics } (which of researcher/sentiment/chartist
        had best predictive power when they were the top signal)
    Also persists a summary row to Supabase strategy_performance table.
    """
    try:
        from dine_trade.storage.supabase_client import select_trade_outcomes_since, insert_strategy_performance
    except Exception as e:
        logger.warning("Supabase not available for strategy metrics: %s", e)
        return _empty_metrics(lookback_days)

    try:
        outcomes = select_trade_outcomes_since(lookback_days)
    except Exception as e:
        logger.warning("Failed to fetch trade outcomes: %s", e)
        outcomes = []

    if not outcomes:
        result = _empty_metrics(lookback_days)
        _store_strategy_performance_safe(lookback_days, result)
        return result

    pnls = []
    for o in outcomes:
        try:
            p = float(o.get("pnl", 0))
        except (TypeError, ValueError):
            p = 0.0
        pnls.append(p)

    overall = _metrics_from_pnls(pnls)

    by_regime: Dict[str, Dict[str, Any]] = {}
    for o in outcomes:
        regime = (o.get("market_regime") or "unknown").lower()
        if regime not in by_regime:
            by_regime[regime] = []
        try:
            by_regime[regime].append(float(o.get("pnl", 0)))
        except (TypeError, ValueError):
            by_regime[regime].append(0.0)
    by_regime_metrics = {r: _metrics_from_pnls(pl) for r, pl in by_regime.items()}

    by_asset: Dict[str, List[float]] = {}
    for o in outcomes:
        ac = (o.get("asset_class") or "EQUITY").upper()
        if ac not in by_asset:
            by_asset[ac] = []
        try:
            by_asset[ac].append(float(o.get("pnl", 0)))
        except (TypeError, ValueError):
            by_asset[ac].append(0.0)
    by_asset_class = {ac: _metrics_from_pnls(pl) for ac, pl in by_asset.items()}

    by_agent: Dict[str, List[float]] = {}
    for o in outcomes:
        agent = _agent_key_from_verdicts(o.get("agent_verdicts"))
        if agent not in by_agent:
            by_agent[agent] = []
        try:
            by_agent[agent].append(float(o.get("pnl", 0)))
        except (TypeError, ValueError):
            by_agent[agent].append(0.0)
    by_agent_metrics = {a: _metrics_from_pnls(pl) for a, pl in by_agent.items()}

    result = {
        "lookback_days": lookback_days,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "win_rate": overall["win_rate"],
        "avg_winner": overall["avg_winner"],
        "avg_loser": overall["avg_loser"],
        "sharpe": overall["sharpe"],
        "max_drawdown": overall["max_drawdown"],
        "n_trades": overall["n_trades"],
        "by_regime": by_regime_metrics,
        "by_asset_class": by_asset_class,
        "by_agent": by_agent_metrics,
    }
    _store_strategy_performance_safe(lookback_days, result)
    return result


def _empty_metrics(lookback_days: int) -> Dict[str, Any]:
    return {
        "lookback_days": lookback_days,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "win_rate": 0.0,
        "avg_winner": 0.0,
        "avg_loser": 0.0,
        "sharpe": 0.0,
        "max_drawdown": 0.0,
        "n_trades": 0,
        "by_regime": {},
        "by_asset_class": {},
        "by_agent": {},
    }


def _store_strategy_performance_safe(lookback_days: int, result: Dict[str, Any]) -> None:
    """Persist computed metrics to Supabase strategy_performance table."""
    try:
        from dine_trade.storage.supabase_client import insert_strategy_performance
        row = {
            "lookback_days": lookback_days,
            "computed_at": result["computed_at"],
            "win_rate": result["win_rate"],
            "avg_winner": result["avg_winner"],
            "avg_loser": result["avg_loser"],
            "sharpe": result["sharpe"],
            "max_drawdown": result["max_drawdown"],
            "n_trades": result["n_trades"],
            "by_regime": result["by_regime"],
            "by_asset_class": result["by_asset_class"],
            "by_agent": result["by_agent"],
        }
        insert_strategy_performance(row)
    except Exception as e:
        logger.warning("Failed to insert strategy_performance: %s", e)
