"""Full pipeline script.

Phase 3 audit flow:
  - Load config (env-backed settings).
  - Fetch OHLCV and headlines.
  - Run async consensus (Researcher, Sentiment, Chartist, then Risk Officer).
  - If consensus approved: Executor (DataValidator + smart_limit_order).
  - On daily drawdown >= 1.5%: circuit breaker + write_post_mortem(...), then exit/pause.

Run from project root:
    python scripts/run_consensus_trade.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

# Ensure project root is on sys.path so that `dine_trade` can be imported
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dine_trade.config.logging_config import setup_logging
from dine_trade.config.settings import DAILY_DRAWDOWN_LIMIT_PCT, TRADING_ENABLED, UNIVERSE_DEFAULT
from dine_trade.data.providers import (
    get_latest_price_with_failover,
    get_ohlcv_with_failover,
)
from dine_trade.data.feeds import get_recent_headlines
from dine_trade.orchestration.consensus import run_consensus
from dine_trade.agents.executor import run_executor
from dine_trade.risk.limits import (
    build_failure_state,
    compute_daily_drawdown,
    should_trigger_circuit_breaker,
)
from dine_trade.storage.post_mortem import write_post_mortem


logger = setup_logging("dine_trade.run_consensus_trade", log_file_prefix="consensus")


def _get_symbol_from_args() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1].upper()
    return UNIVERSE_DEFAULT[0]


async def main() -> None:
    symbol = _get_symbol_from_args()
    logger.info("Running consensus trade pipeline for %s", symbol)

    if not TRADING_ENABLED:
        logger.warning("TRADING_ENABLED is false; trading is disabled. Exiting without orders.")
        return

    # 1) Load data: OHLCV and headlines
    logger.info("Fetching OHLCV and headlines for %s", symbol)
    ohlcv_df = get_ohlcv_with_failover(symbol, days=100)
    headlines = get_recent_headlines(symbol, limit=10)

    if ohlcv_df is None or getattr(ohlcv_df, "empty", True):
        logger.warning("No OHLCV data for %s; aborting.", symbol)
        return

    # Price sources for DataValidator: bars close and latest quote mid (with failover)
    price_from_bars = float(ohlcv_df["close"].iloc[-1])
    latest_mid = get_latest_price_with_failover(symbol)
    if latest_mid is None:
        logger.warning("No latest quote mid for %s; aborting.", symbol)
        return

    # 2) Mock/simple account context (Phase 3): assume equity from env/data provider later
    # For now, require user to specify equity via CLI or placeholder.
    # Here we use a simple placeholder; in production wire to Alpaca account equity.
    account_equity = 100_000.0

    # Positions placeholder (Phase 3: single-symbol flat start)
    positions: List[Dict[str, Any]] = []

    logger.info("Running async consensus for %s", symbol)
    consensus = await run_consensus(
        symbol=symbol,
        account_equity=account_equity,
        positions=positions,
        ohlcv_df=ohlcv_df,
        headlines=headlines,
    )

    logger.info("Consensus result for %s: approved=%s, reason=%s, suggested_qty=%.4f",
                symbol, consensus.get("approved"), consensus.get("reason"), consensus.get("suggested_qty", 0.0))

    # If consensus not approved, no order.
    if not consensus.get("approved"):
        logger.info("Consensus not approved; no order will be sent.")
        return

    # 3) Compute current daily drawdown and check circuit breaker BEFORE execution
    # In Phase 3, use a simple equity_at_open = account_equity for demo.
    equity_at_open = account_equity
    # In production, current_equity should be fetched live; here we reuse account_equity.
    current_equity = account_equity
    dd_pct = compute_daily_drawdown(equity_at_open, current_equity)
    logger.info("Current daily drawdown: %.4f%% (limit=%.4f%%)", dd_pct, DAILY_DRAWDOWN_LIMIT_PCT)

    if should_trigger_circuit_breaker(dd_pct):
        logger.warning("Daily drawdown %.4f%% >= limit %.4f%% — triggering circuit breaker.", dd_pct, DAILY_DRAWDOWN_LIMIT_PCT)
        failure_state = build_failure_state(
            equity_at_open=equity_at_open,
            current_equity=current_equity,
            positions_snapshot={"positions": positions},
            sentiment_snapshot=consensus.get("agent_results", {}).get("sentiment", {}),
            charts_snapshot=consensus.get("agent_results", {}).get("chartist", {}),
            agent_summary=consensus,
        )
        try:
            write_post_mortem(failure_state)
            logger.info("Post-mortem written to Supabase.")
        except Exception as e:  # pragma: no cover
            logger.exception("Failed to write post-mortem: %s", e)
        logger.warning("Circuit breaker active; no orders will be sent. Exiting.")
        return

    # 4) Executor: DataValidator + smart_limit_order with Risk Officer re-check
    executor_result = run_executor(
        consensus | {"symbol": symbol},
        price_a=price_from_bars,
        price_b=float(latest_mid),
        account_equity=account_equity,
        daily_drawdown_pct=dd_pct,
    )

    logger.info(
        "Executor result for %s: status=%s, qty=%.4f, order_id=%s, reason=%s",
        symbol,
        executor_result.get("status"),
        executor_result.get("qty", 0.0),
        executor_result.get("order_id"),
        executor_result.get("reason"),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
