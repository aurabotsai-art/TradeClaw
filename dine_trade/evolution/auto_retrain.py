"""Parameter auto-tuning via Bayesian Optimization (Optuna).

Periodically re-optimizes key strategy parameters using recent data and
walk-forward backtests:

  - ATR stop multiplier (default 2.0 in risk.atm_stop_loss)
  - Consensus score threshold (default 7 in orchestration.consensus)
  - Kelly fraction cap (default half-Kelly = 0.5 in risk.kelly / risk_officer)
  - TWAP/VWAP duration proxy (number of TWAP slices)

Method:
  - Uses Optuna Bayesian optimization to search parameter space.
  - For each trial, runs a walk-forward backtest on recent OHLCV data using
    the rule-based surrogate signals (no Gemini calls).
  - Objective is to maximize out-of-sample Sharpe.

Constraints:
  - NEVER auto-tune with live money. This module checks PAPER_MODE and will
    raise if PAPER_MODE is False.
  - Auto-tuning should be run on a scheduled job (e.g. weekly on Sunday).
  - Parameters are only updated if Sharpe improves by more than 10% over the
    current/baseline configuration.

Results are written to the Supabase `strategy_params` table; live components
can read from there and apply the tuned values after manual review.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict

import pandas as pd

from dine_trade.backtesting.walk_forward import WalkForwardSummary, walk_forward_test
from dine_trade.config.settings import PAPER_MODE, UNIVERSE_DEFAULT
from dine_trade.data.providers import get_ohlcv_with_failover

logger = logging.getLogger(__name__)

try:  # Optuna is optional dependency
    import optuna  # type: ignore[import]
except Exception:  # pragma: no cover
    optuna = None  # type: ignore[assignment]


@dataclass
class TunableParams:
    """Key strategy parameters subject to auto-tuning."""

    atr_mult: float = 2.0
    consensus_threshold: float = 7.0
    kelly_fraction_cap: float = 0.5
    twap_slices: int = 4


DEFAULT_PARAMS = TunableParams()


def _ensure_paper_mode() -> None:
    """Guard against running auto-tuning when live trading is enabled."""
    if not PAPER_MODE:
        raise RuntimeError(
            "Auto-tuning is restricted to paper/simulation mode. "
            "Set PAPER_MODE=true and run against out-of-sample data only."
        )


def _load_ohlcv_universe(days: int = 365) -> Dict[str, pd.DataFrame]:
    """Fetch recent OHLCV for each symbol in UNIVERSE_DEFAULT."""
    data: Dict[str, pd.DataFrame] = {}
    for sym in UNIVERSE_DEFAULT:
        try:
            df = get_ohlcv_with_failover(sym, days=days)
        except Exception as e:  # pragma: no cover - network/remote errors
            logger.warning("Failed to load OHLCV for %s during auto-tune: %s", sym, e)
            continue
        if df is None or getattr(df, "empty", True):
            logger.warning("Empty OHLCV for %s during auto-tune; skipping symbol.", sym)
            continue
        data[sym] = df
    return data


def run_walk_forward(params: Dict[str, Any], *, days: int = 365) -> Dict[str, Any]:
    """Run walk-forward backtests across the default universe with given params.

    Notes:
      - Currently, the main lever affecting the walk-forward Sharpe is the
        effective risk per trade, which we map from `kelly_fraction_cap`.
      - ATR multiplier, consensus threshold, and TWAP slices are included in
        the parameter set and stored in Supabase, but their live effects are
        applied in the real-time strategy (risk/execution/consensus), not in
        this surrogate backtester yet.
    """
    universe_data = _load_ohlcv_universe(days=days)
    if not universe_data:
        return {"avg_sharpe": 0.0, "by_symbol": {}}

    # Map Kelly cap (0..1) to risk_per_trade_pct in [0.25, 2.0] as a simple proxy.
    kelly_cap = float(params.get("kelly_fraction_cap", DEFAULT_PARAMS.kelly_fraction_cap) or 0.5)
    kelly_cap = max(0.05, min(kelly_cap, 1.0))
    risk_per_trade_pct = 0.25 + (2.0 - 0.25) * kelly_cap  # 0.25% .. 2.0%

    by_symbol: Dict[str, float] = {}
    sharpes: list[float] = []

    for sym, df in universe_data.items():
        try:
            summary: WalkForwardSummary = walk_forward_test(
                sym,
                df,
                train_size=252,
                test_size=63,
                initial_equity=100_000.0,
                risk_per_trade_pct=risk_per_trade_pct,
                slippage_bps=1.0,
            )
        except Exception as e:  # pragma: no cover
            logger.warning("Walk-forward test failed for %s: %s", sym, e)
            continue

        by_symbol[sym] = float(summary.avg_sharpe)
        sharpes.append(summary.avg_sharpe)

    avg_sharpe = float(sum(sharpes) / len(sharpes)) if sharpes else 0.0
    return {"avg_sharpe": avg_sharpe, "by_symbol": by_symbol}


def _objective_factory(days: int = 365):
    """Build Optuna objective using run_walk_forward."""

    def objective(trial: "optuna.trial.Trial") -> float:  # type: ignore[name-defined]
        atr_mult = trial.suggest_float("atr_mult", 1.5, 3.5)
        threshold = trial.suggest_float("consensus_threshold", 6.0, 9.0)
        kelly_cap = trial.suggest_float("kelly_fraction_cap", 0.1, 1.0)
        twap_slices = trial.suggest_int("twap_slices", 2, 12)

        params = {
            "atr_mult": atr_mult,
            "consensus_threshold": threshold,
            "kelly_fraction_cap": kelly_cap,
            "twap_slices": twap_slices,
        }
        result = run_walk_forward(params=params, days=days)
        sharpe = float(result.get("avg_sharpe", 0.0) or 0.0)
        return sharpe

    return objective


def optimize_parameters(
    *,
    days: int = 365,
    n_trials: int = 50,
    random_seed: int | None = 42,
) -> Dict[str, Any]:
    """Run Optuna-based Bayesian optimization for key parameters.

    Returns a dict:
      {
        "best_params": {...},
        "best_sharpe": float,
        "study_summary": {...},
      }
    """
    _ensure_paper_mode()
    if optuna is None:
        raise RuntimeError("optuna is not installed; run `pip install optuna` to enable auto-tuning.")

    sampler = optuna.samplers.TPESampler(seed=random_seed)
    study = optuna.create_study(direction="maximize", sampler=sampler)
    study.optimize(_objective_factory(days=days), n_trials=n_trials)

    best_params = study.best_params
    best_value = float(study.best_value)

    # Minimal serializable summary; avoid dumping large trial history
    summary = {
        "n_trials": len(study.trials),
        "best_value": best_value,
        "best_trial_number": study.best_trial.number,
    }
    return {
        "best_params": best_params,
        "best_sharpe": best_value,
        "study_summary": summary,
    }


def auto_tune_weekly(
    *,
    days: int = 365,
    improvement_threshold: float = 0.10,
    n_trials: int = 50,
) -> Dict[str, Any]:
    """Entry point for weekly auto-tuning job (run on Sundays).

    - Evaluates baseline Sharpe using the latest stored params (or defaults).
    - Runs Optuna optimization for `n_trials`.
    - Writes new params to Supabase `strategy_params` only if Sharpe improves
      by more than `improvement_threshold` (e.g. 0.10 = +10%).
    """
    _ensure_paper_mode()

    from dine_trade.storage.supabase_client import (  # local import to avoid cycles
        get_latest_strategy_params,
        insert_strategy_params,
    )

    latest = get_latest_strategy_params() or {}

    # Baseline params from last row or defaults
    baseline_params = TunableParams(
        atr_mult=float(latest.get("atr_mult", DEFAULT_PARAMS.atr_mult) or DEFAULT_PARAMS.atr_mult),
        consensus_threshold=float(
            latest.get("consensus_threshold", DEFAULT_PARAMS.consensus_threshold)
            or DEFAULT_PARAMS.consensus_threshold
        ),
        kelly_fraction_cap=float(
            latest.get("kelly_fraction_cap", DEFAULT_PARAMS.kelly_fraction_cap)
            or DEFAULT_PARAMS.kelly_fraction_cap
        ),
        twap_slices=int(latest.get("twap_slices", DEFAULT_PARAMS.twap_slices) or DEFAULT_PARAMS.twap_slices),
    )

    baseline_result = run_walk_forward(params=asdict(baseline_params), days=days)
    baseline_sharpe = float(baseline_result.get("avg_sharpe", 0.0) or 0.0)

    opt_result = optimize_parameters(days=days, n_trials=n_trials)
    best_params = opt_result["best_params"]
    best_sharpe = float(opt_result.get("best_sharpe", 0.0) or 0.0)

    if baseline_sharpe <= 0 and best_sharpe <= 0:
        improvement_pct = 0.0
    elif baseline_sharpe <= 0:
        improvement_pct = float("inf")
    else:
        improvement_pct = (best_sharpe - baseline_sharpe) / abs(baseline_sharpe)

    should_update = improvement_pct > improvement_threshold

    tuned_at = datetime.now(timezone.utc).isoformat()
    row = {
        "tuned_at": tuned_at,
        "atr_mult": float(best_params.get("atr_mult", baseline_params.atr_mult)),
        "consensus_threshold": float(
            best_params.get("consensus_threshold", baseline_params.consensus_threshold)
        ),
        "kelly_fraction_cap": float(best_params.get("kelly_fraction_cap", baseline_params.kelly_fraction_cap)),
        "twap_slices": int(best_params.get("twap_slices", baseline_params.twap_slices)),
        "baseline_sharpe": baseline_sharpe,
        "tuned_sharpe": best_sharpe,
        "improvement_pct": float(improvement_pct if improvement_pct != float("inf") else 1e9),
        "details": opt_result.get("study_summary", {}),
    }

    if should_update:
        insert_strategy_params(row)
        logger.info(
            "Auto-tune accepted new params (Sharpe %.3f -> %.3f, improvement %.1f%%).",
            baseline_sharpe,
            best_sharpe,
            improvement_pct * 100 if improvement_pct != float("inf") else 100.0,
        )
    else:
        logger.info(
            "Auto-tune rejected params (Sharpe %.3f -> %.3f, improvement %.1f%% <= threshold %.1f%%).",
            baseline_sharpe,
            best_sharpe,
            improvement_pct * 100 if improvement_pct != float("inf") else 100.0,
            improvement_threshold * 100,
        )

    return {
        "baseline_sharpe": baseline_sharpe,
        "best_sharpe": best_sharpe,
        "improvement_pct": improvement_pct,
        "accepted": bool(should_update),
        "params": {
            "baseline": asdict(baseline_params),
            "tuned": {
                "atr_mult": row["atr_mult"],
                "consensus_threshold": row["consensus_threshold"],
                "kelly_fraction_cap": row["kelly_fraction_cap"],
                "twap_slices": row["twap_slices"],
            },
        },
    }

