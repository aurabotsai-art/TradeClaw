"""Smoke tests for individual agents (Researcher, Analyst, Sentiment, Chartist, Risk Officer).

Run from project root:
    python scripts/smoke_test_agents.py
"""
from __future__ import annotations

import os
import pprint
import sys

import pandas as pd

# Ensure project root on sys.path (same pattern as run_paper_phase1)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dine_trade.agents.analyst import get_conviction_score
from dine_trade.agents.researcher import run_researcher
from dine_trade.agents.sentiment import run_sentiment
from dine_trade.agents.chartist import run_chartist
from dine_trade.agents.risk_officer import run_risk_officer
from dine_trade.config.settings import GEMINI_MODEL_RESEARCHER, GEMINI_MODEL_FAST


def _fake_ohlcv() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=30),
            "open": [100 + i * 0.5 for i in range(30)],
            "high": [101 + i * 0.5 for i in range(30)],
            "low": [99 + i * 0.5 for i in range(30)],
            "close": [100 + i * 0.5 for i in range(30)],
            "volume": [1_000_000 + i * 10_000 for i in range(30)],
        }
    )


def main() -> int:
    symbol = "NVDA"
    ohlcv_df = _fake_ohlcv()
    headlines = [
        {"title": "Sample positive headline for NVDA", "published_at": "2024-01-01", "source": "TEST"},
        {"title": "Another neutral NVDA news item", "published_at": "2024-01-02", "source": "TEST"},
    ]
    fundamentals = {"PE": 25.3, "Debt/Equity": 0.4}
    sec_ctx = "Sample SEC 10-K snippet about NVDA fundamentals and risks."

    print("GEMINI_MODEL_RESEARCHER =", GEMINI_MODEL_RESEARCHER)
    print("GEMINI_MODEL_FAST =", GEMINI_MODEL_FAST)

    print("\n=== Researcher ===")
    researcher_res = run_researcher(symbol, ohlcv_df=ohlcv_df, fundamentals=fundamentals, sec_context=sec_ctx)
    pprint.pp(researcher_res)

    print("\n=== Phase 1 Analyst Conviction ===")
    score, reasoning = get_conviction_score(ohlcv_df, headlines, symbol)
    pprint.pp({"score": score, "reasoning": reasoning})

    print("\n=== Sentiment ===")
    sentiment_res = run_sentiment(symbol, headlines)
    pprint.pp(sentiment_res)

    print("\n=== Chartist ===")
    chartist_res = run_chartist(symbol, ohlcv_df)
    pprint.pp(chartist_res)

    print("\n=== Risk Officer ===")
    risk_res = run_risk_officer(
        symbol=symbol,
        price=float(ohlcv_df["close"].iloc[-1]),
        account_equity=100_000.0,
        position_size_usd=5_000.0,
        qty=50,
        volatility=None,
        daily_drawdown_pct=0.5,
    )
    pprint.pp(risk_res)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

