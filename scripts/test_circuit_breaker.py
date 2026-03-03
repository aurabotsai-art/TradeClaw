"""
Test script for the daily drawdown circuit breaker and post_mortem logging.

This does NOT place any orders.
It:
  - fetches OHLCV + headlines,
  - runs async consensus (Researcher, Sentiment, Chartist, Risk Officer),
  - simulates a daily drawdown slightly above the configured limit,
  - builds a failure_state and writes it via write_post_mortem(...).

Run from project root:
    python scripts/test_circuit_breaker.py [SYMBOL]
"""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Dict, List


def _ensure_root_on_path() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(script_dir)
    if root not in sys.path:
        sys.path.insert(0, root)
    return root


_ROOT = _ensure_root_on_path()

from dine_trade.config.settings import (  # noqa: E402
    DAILY_DRAWDOWN_LIMIT_PCT,
    UNIVERSE_DEFAULT,
)
from dine_trade.data.connectors.alpaca_connector import (  # noqa: E402
    get_ohlcv,
)
from dine_trade.data.feeds.news_feed import get_recent_headlines  # noqa: E402
from dine_trade.orchestration.consensus import run_consensus  # noqa: E402
from dine_trade.risk.limits import (  # noqa: E402
    build_failure_state,
    compute_daily_drawdown,
    should_trigger_circuit_breaker,
)
from dine_trade.storage.post_mortem import write_post_mortem  # noqa: E402


async def _run(symbol: str) -> int:
    account_equity = 100_000.0

    print(f"[test_circuit_breaker] Symbol={symbol}, equity={account_equity:,.2f}")
    print("[1/4] Fetching OHLCV and headlines...")
    ohlcv_df = get_ohlcv(symbol, days=100)
    if ohlcv_df is None or getattr(ohlcv_df, "empty", True):
        print("  ERROR: No OHLCV data returned; aborting.")
        return 1
    headlines = get_recent_headlines(symbol, limit=10)

    print("[2/4] Running async consensus (no execution)...")
    positions: List[Dict[str, Any]] = []
    consensus = await run_consensus(
        symbol=symbol,
        account_equity=account_equity,
        positions=positions,
        ohlcv_df=ohlcv_df,
        headlines=headlines,
    )

    print(
        f"  Consensus approved={consensus.get('approved')} "
        f"reason={consensus.get('reason')}"
    )

    print("[3/4] Simulating daily drawdown above limit to trigger circuit breaker...")
    equity_at_open = account_equity

    # Simulate a drawdown slightly above the configured limit (e.g. if limit is 1.5%,
    # use ~1.6%).
    simulated_dd_pct = float(DAILY_DRAWDOWN_LIMIT_PCT) + 0.1
    current_equity = equity_at_open * (1.0 - simulated_dd_pct / 100.0)

    dd_pct = compute_daily_drawdown(equity_at_open, current_equity)
    print(
        f"  Configured limit={DAILY_DRAWDOWN_LIMIT_PCT:.4f}% "
        f"simulated_dd={dd_pct:.4f}%"
    )

    if not should_trigger_circuit_breaker(dd_pct):
        print("  ERROR: simulated drawdown did not breach the circuit breaker limit.")
        return 1

    print("[4/4] Building failure_state and writing post_mortem...")
    agent_results = consensus.get("agent_results", {})
    sentiment_snapshot = agent_results.get("sentiment", {})
    charts_snapshot = agent_results.get("chartist", {})

    failure_state = build_failure_state(
        equity_at_open=equity_at_open,
        current_equity=current_equity,
        positions_snapshot={"positions": positions},
        sentiment_snapshot=sentiment_snapshot,
        charts_snapshot=charts_snapshot,
        agent_summary=consensus,
    )

    write_post_mortem(failure_state)
    print("  SUCCESS: post_mortem row should now be present in Supabase.")
    print("  Check the `post_mortem` table ordered by triggered_at DESC.")
    return 0


def main() -> int:
    if len(sys.argv) > 1:
        symbol = sys.argv[1].upper()
    else:
        symbol = (UNIVERSE_DEFAULT or ["NVDA"])[0]

    return asyncio.run(_run(symbol))


if __name__ == "__main__":
    raise SystemExit(main())

