"""Smoke test for async consensus orchestration.

Run from project root:
    python scripts/smoke_test_consensus.py
"""
from __future__ import annotations

import asyncio
import os
import time
import sys

import pandas as pd

# Ensure project root on sys.path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dine_trade.orchestration import run_consensus


def _fake_ohlcv() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=60),
            "open": [100 + i * 0.5 for i in range(60)],
            "high": [101 + i * 0.5 for i in range(60)],
            "low": [99 + i * 0.5 for i in range(60)],
            "close": [100 + i * 0.5 for i in range(60)],
            "volume": [1_000_000 + i * 10_000 for i in range(60)],
        }
    )


async def _run() -> int:
    symbol = "NVDA"
    ohlcv_df = _fake_ohlcv()
    headlines = [
        {"title": "Sample NVDA headline for consensus test", "published_at": "2024-01-01", "source": "TEST"}
    ]
    account_equity = 100_000.0
    positions: list[dict] = []

    t0 = time.perf_counter()
    result = await run_consensus(
        symbol=symbol,
        account_equity=account_equity,
        positions=positions,
        ohlcv_df=ohlcv_df,
        headlines=headlines,
        score_threshold=7.0,
        qty=50,
    )
    t1 = time.perf_counter()

    print("Consensus result:")
    from pprint import pp

    pp(result)
    print(f"\nTotal orchestration time: {t1 - t0:.2f} seconds")

    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())

