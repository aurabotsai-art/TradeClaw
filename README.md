# DineTrade

Modular, multi-agent algorithmic trading system with a **risk-first** consensus protocol. Trades execute via Alpaca only when four specialist agents (Researcher, Sentiment, Chartist, Risk Officer) agree and pass a 1.5% daily drawdown limit.

## Stack

- **Brain:** Gemini 1.5 Pro (Researcher), Gemini 1.5 Flash (Sentiment, Chartist)
- **Execution:** Alpaca (smart limit at mid-price, 60s TIF)
- **Data:** Alpaca (OHLCV + quote); Polygon optional; FMP for news
- **Storage:** Supabase (trade_log, daily_state, agent_runs, post_mortem), Redis optional
- **Orchestration:** Async consensus via `asyncio.gather`

## Setup

1. Copy `.env.example` to `.env` and fill API keys.
2. `python -m venv .venv` then activate and `pip install -r requirements.txt`.
3. Run paper Phase 1: `python scripts/run_paper_phase1.py`.
4. Full consensus pipeline: `python scripts/run_consensus_trade.py`.

## Audit / Production

- **DataValidator:** Two price sources (e.g. Alpaca bars vs Alpaca quote) within 0.1% before any trade.
- **RegimeTest:** Backtest 2022 Tech Bear and August 2024 Volatility before live.
- **Recovery:** On 1.5% daily DD, write failure state (positions, sentiment, charts) to Supabase `post_mortem`.

See `Plan-Phase-1-6.md` for the full phased build plan.
