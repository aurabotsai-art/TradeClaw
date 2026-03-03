---
name: DineTrade Full Build Plan
overview: "Production-grade DineTrade: risk-first multi-agent trading with Model Hybridization (Pro/Flash), smart limit execution, DataValidator, async orchestration, RegimeTest, and post_mortem recovery. Gemini 1.5 Pro (Researcher only), Gemini 1.5 Flash (Sentiment + Chartist), Alpaca, Supabase/Redis, 1.5% daily drawdown with post_mortem on breach."
todos: []
isProject: false
---

# DineTrade: Full Finalized Expanded Executable Plan (Production-Grade Audit Refactor)

**Audit requirements applied:** Model Hybridization, Smart Limit Order (mid-price, 60s), DataValidator (two price sources within 0.1%), Async Orchestration (asyncio.gather), RegimeTest (2022 Tech Bear + Aug 2024 Volatility), Recovery Protocol (post_mortem to Supabase on 1.5% DD).

This plan is structured so you can execute it phase-by-phase. Standalone refactored Phases 1–6: [Plan-Phase-1-6.md](c:\Users\muham\Downloads\trade bot\Plan-Phase-1-6.md).

---

## Phase 0: Prerequisites and Environment Setup

**Goal:** Reproducible Python 3.12+ environment, API keys, and folder skeleton. No trading logic yet.

### 0.1 Manual: API Keys and Accounts

- **Google AI (Gemini):** Create key at [aistudio.google.com](https://aistudio.google.com) → Get API key. Store as `GEMINI_API_KEY`.
- **Alpaca:** Sign up at [alpaca.markets](https://alpaca.markets) → Paper trading enabled by default. Generate API Key + Secret. Store as `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, `APCA_API_BASE_URL` = `https://paper-api.alpaca.markets`.
- **Polygon.io (optional for Phase 1):** Sign up, get key for real-time data later. Store as `POLYGON_API_KEY`.
- **Financial Modeling Prep (FMP):** Sign up at [financialmodelingprep.com](https://financialmodelingprep.com), get API key. Store as `FMP_API_KEY`.
- **Supabase:** Create project at [supabase.com](https://supabase.com). Note `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` (or anon key for minimal scope).
- **Redis:** Plan for local Redis (Docker) or Upstash for serverless. No key needed for local.

### 0.2 Project Skeleton (Execute in project root: `c:\Users\muham\Downloads\trade bot`)

```text
Create folder structure:
  dine_trade/
    __init__.py
    config/
      __init__.py
      settings.py          # GEMINI_MODEL_RESEARCHER, GEMINI_MODEL_FAST
    data/
      __init__.py
      connectors/
        __init__.py
        alpaca_connector.py
        polygon_connector.py
      feeds/
        __init__.py
    agents/
      __init__.py
      researcher/          # gemini-3.1-pro-preview only
      sentiment/           # gemini-3-flash-preview
      chartist/            # gemini-3-flash-preview
      risk_officer/
      executor/
    orchestration/
      __init__.py
      consensus.py         # asyncio.gather for parallel agents
    execution/
      __init__.py
      alpaca_client.py     # smart_limit_order (mid-price, 60s TIF)
    storage/
      __init__.py
      supabase_client.py   # trade_log, daily_state, agent_runs, post_mortem
      redis_client.py
    risk/
      __init__.py
      limits.py
      kelly.py
      kill_switch.py
    utils/
      __init__.py
      data_validator.py    # two price sources within 0.1%
    backtesting/
      __init__.py
      regime_test.py      # 2022 Tech Bear, Aug 2024 Volatility
    logs/
      (gitkeep)
  tests/
    __init__.py
  scripts/
    run_paper_phase1.py
    run_consensus_trade.py
  .env.example
  .gitignore
  requirements.txt
  README.md
```

### 0.3 Python Environment and Dependencies

- **Manual:** Install Python 3.12+ (verify with `python --version`).
- Create venv and install (copy-paste):

```bash
cd "c:\Users\muham\Downloads\trade bot"
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
```

- **requirements.txt (initial):**

```text
python-dotenv>=1.0.0
google-generativeai>=0.8.0
alpaca-trade-api>=3.0.0
requests>=2.31.0
pandas>=2.0.0
numpy>=1.24.0
supabase>=2.0.0
redis>=5.0.0
langgraph>=0.0.20
langchain-google-genai>=2.0.0
```

- Run: `pip install -r requirements.txt`
- **Manual:** Copy `.env.example` to `.env` and fill in all keys (never commit `.env`).

### 0.4 Config and Constants

- **config/settings.py:** Load from `os.environ`: `GEMINI_API_KEY`, `APCA_*`, `FMP_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `POLYGON_API_KEY` (if any). Define constants: `DAILY_DRAWDOWN_LIMIT_PCT = 1.5`, `MAX_RISK_PER_TRADE_PCT = 1.0`, `PAPER_MODE = True`, `UNIVERSE_DEFAULT = ["NVDA"]`. **Model hybridization:** `GEMINI_MODEL_RESEARCHER = "gemini-3.1-pro-preview"`, `GEMINI_MODEL_FAST = "gemini-3-flash-preview"`.

---

## Phase 1: The 48-Hour Paper Skeleton (Production-Grade)

**Goal:** Data Connector → Gemini Analyst → **DataValidator** (two price sources within 0.1%) → **Smart limit order** (mid-price, 60s expiration) on Alpaca paper. No multi-agent yet.

### 1.1 Data Connector (Alpaca)

- **data/connectors/alpaca_connector.py**
  - `get_ohlcv(symbol, days=100) -> pd.DataFrame`: Alpaca daily equity history; columns `date`, `open`, `high`, `low`, `close`, `volume`.
  - **Add:** `get_latest_price(symbol: str) -> float`: latest quote mid or last close for DataValidator.
  - **Manual:** Verify NVDA 100-day fetch and `get_latest_price`.

### 1.2 News Headlines (Minimal)

- **data/feeds/news_feed.py**
  - `get_recent_headlines(symbol, limit=10) -> list[dict]`: FMP/NewsAPI; keys `title`, `published_at`, `source`.

### 1.3 Gemini Analyst (Conviction Score)

- **agents/analyst/gemini_analyst.py**
  - Phase 1 single analyst: use **gemini-3.1-pro-preview** (`GEMINI_MODEL_RESEARCHER`) for consistency with future Researcher.
  - `get_conviction_score(ohlcv_df, headlines, symbol) -> tuple[float, str]`: OHLCV summary + headlines; prompt for SCORE 1–10 and REASONING; parse and return.

### 1.4 Hard-Coded Safety Constraint (Anti-Hallucination)

- **risk/limits.py**
  - `price_vs_ma_allowed(price, ma20, max_deviation_pct=5.0) -> bool`: allow only if price within 5% of 20-day MA.

### 1.5 DataValidator (Audit: Data Sanity Check)

- **utils/data_validator.py**
  - **Required before any trade.** `validate_price_agreement(price_a, price_b, tolerance_pct=0.1) -> tuple[bool, str]`: deviation = |price_a - price_b|/price_b * 100; return (True,"OK") if <= 0.1%, else (False, message). Used in Phase 1 script and Executor (Phase 3).

### 1.6 Execution: Smart Limit Order (Audit: Replace Market Buy)

- **execution/alpaca_client.py**
  - **Remove** `submit_market_buy` as primary path. **Add:** `get_latest_quote(symbol) -> dict` (bid, ask from Alpaca). **Add:** `smart_limit_order(symbol, side, qty, time_in_force_sec=60) -> dict`: mid_price = (bid+ask)/2; submit **limit order** at mid_price, 60s expiration (e.g. submit limit + cancel-after-60s); return order response. Keep `get_account()`.

### 1.7 Phase 1 Orchestration Script

- **scripts/run_paper_phase1.py**
  - Fetch OHLCV and headlines; 20-day MA and `price_vs_ma_allowed`; Gemini `get_conviction_score`. **Before any order:** get OHLCV-based price (e.g. from bars) and Alpaca live quote mid; call `DataValidator.validate_price_agreement(price_from_bars, price_from_quote, 0.1)`; if invalid, abort and log. If score > 8 and MA and DataValidator pass: call `**smart_limit_order("NVDA", "buy", qty, 60)`**. Log to console and `logs/phase1_YYYYMMDD.log`.

### 1.8 Manual Verification

- Run script; confirm data load, Gemini score, **DataValidator pass/fail**, and **limit order at mid with 60s** on Alpaca paper. Test with forced price divergence to confirm order aborted.

---

## Phase 2: Multi-Agent Foundation

**Goal:** Implement the four specialist agents (Researcher, Sentiment, Chartist, Risk Officer) and a simple orchestration flow. No execution yet; agents return votes/reasoning.

### 2.1 Researcher Agent (Fundamental) — Gemini 1.5 Pro Only

- **agents/researcher/agent.py**
  - **Model:** **gemini-3.1-pro-preview** (`GEMINI_MODEL_RESEARCHER`). Inputs: symbol, ohlcv_df, fundamental dict, SEC context from recent filings/financials.
  - Prompt: VERDICT + SCORE 1-10 + reasoning. Return: `{"verdict": "APPROVE"|"REJECT", "score": float, "reasoning": str}`.

### 2.2 Sentiment Agent (Newsroom) — Gemini 1.5 Flash

- **agents/sentiment/agent.py**
  - **Model:** **gemini-3-flash-preview** (`GEMINI_MODEL_FAST`) for high-speed sentiment. Inputs: symbol, headlines. Same return structure.

### 2.3 Chartist Agent (Technical) — Gemini 1.5 Flash

- **agents/chartist/agent.py**
  - **Model:** **gemini-3-flash-preview** (`GEMINI_MODEL_FAST`). Inputs: symbol, ohlcv_df; compute RSI, MACD, MAs. Same return structure.

### 2.4 Risk Officer Agent

- **agents/risk_officer/agent.py**
  - Inputs: `symbol`, `price`, `account_equity`, `position_size_usd` or `qty`, optional `volatility` (e.g. ATR).
  - Enforce: (1) Max risk per trade 1% of equity (from config). (2) Kelly Criterion: implement fractional Kelly (e.g. half-Kelly) for position size cap. (3) Check daily drawdown: if today’s drawdown >= 1.5%, return REJECT.
  - Return: `{"verdict": "APPROVE"|"REJECT", "max_qty": float, "reasoning": str}`.

### 2.5 Kelly and Position Sizing

- **risk/kelly.py**
  - Function `kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float` (or use win/loss ratio).
  - Function `position_size_cap(equity: float, risk_pct: float, volatility: float, kelly_f: float) -> float`: return max notional or shares to respect risk and optional half-Kelly cap.

### 2.6 Orchestration — Async Parallel (Audit: asyncio.gather)

- **orchestration/consensus.py**
  - **Refactor to async.** Input: symbol, account_equity, positions, ohlcv_df, headlines.
  - Run **Researcher, Sentiment, Chartist in parallel** via `**asyncio.gather(researcher_task(), sentiment_task(), chartist_task())`** (use async Gemini or `asyncio.to_thread` for sync calls).
  - Then run Risk Officer. Consensus: all three APPROVE, score threshold (e.g. >= 7), Risk APPROVE. Output: `{"approved", "reason", "suggested_qty", "agent_results"}`.

### 2.7 Manual Steps

- Unit test each agent; confirm Pro vs Flash model names. Run async orchestration; log consensus and timings.

---

## Phase 3: Risk-First Executor, Smart Limit, Recovery Protocol

**Goal:** Executor uses **smart_limit_order** only; **DataValidator** before every order; on 1.5% DD trigger **post_mortem** to Supabase.

### 3.1 Executor Agent

- **agents/executor/agent.py**
  - Input: consensus (`approved`, `suggested_qty`, `symbol`), two price sources (e.g. OHLCV-derived price and live quote mid).
  - If not `approved`: no order; return.
  - Re-check Risk Officer rules (daily drawdown, position size) immediately before sending order.
  - **DataValidator:** `validate_price_agreement(price_a, price_b, 0.1)` before order; if invalid, abort. Call `**smart_limit_order(symbol, "buy", qty, 60)`** (qty capped by Risk’s `max_qty`.
  - Return order ID and status.

### 3.2 Daily Drawdown Circuit Breaker + Recovery Protocol (Audit)

- **risk/limits.py**: Record `equity_at_open`; before every trade compute drawdown_pct; if >= 1.5%: set circuit breaker, block trades, **call post_mortem handler** (do not just stop).
- **storage/post_mortem.py** or **storage/supabase_client.py**: **write_post_mortem(failure_state)**: failure_state = triggered_at, equity_at_open, current_equity, drawdown_pct, **positions_snapshot**, **sentiment_snapshot**, **charts_snapshot**, optional agent_summary. Insert into Supabase `**post_mortem`** table (Phase 4.1).

### 3.3 Trade and State Logging

- **storage/trade_logger.py**: Log trade attempts (symbol, qty, side, limit price, consensus, timestamp) to file and Supabase `trade_log`.

### 3.4 Wiring Full Pipeline

- **scripts/run_consensus_trade.py**: Load config; fetch data; async orchestration; Executor if approved (DataValidator + smart_limit_order); on circuit breaker trigger, call `write_post_mortem(...)` then exit/pause.

### 3.5 Manual Steps

- Run end-to-end paper; verify limit order at mid, 60s. Simulate 1.5% DD; confirm post_mortem row in Supabase with positions, sentiment, charts.

---

## Phase 4: Data Layer, Logging, and Observability

**Goal:** Supabase for persistent state and trade history; Redis for real-time state (optional); structured logging; optional dashboard.

### 4.1 Supabase Schema

- **Manual:** In Supabase SQL editor, create:
  - `trade_log`: id (uuid), symbol, side, qty, price, order_id, alpaca_order_id, consensus_snapshot (jsonb), created_at, strategy_phase.
  - `daily_state`: date (date), equity_at_open, circuit_breaker_fired (boolean), updated_at.
  - `agent_runs`: id, run_id, agent_name, symbol, verdict, score, reasoning, created_at.
  - `**post_mortem`** (Audit: Recovery Protocol): id (uuid), triggered_at (timestamptz), equity_at_open, current_equity, drawdown_pct, positions_snapshot (jsonb), sentiment_snapshot (jsonb), charts_snapshot (jsonb), agent_summary (jsonb), created_at.

### 4.2 Supabase Client

- **storage/supabase_client.py**
  - Insert into `trade_log`, upsert `daily_state`, insert `agent_runs`, **insert `post_mortem`** (for `write_post_mortem`). Use service role or anon key with RLS as appropriate.

### 4.3 Redis (Optional for Phase 4)

- **storage/redis_client.py**
  - Store `equity_at_open`, `circuit_breaker`, `last_trade_time` for fast access. Key TTL 24h for daily state.

### 4.4 Structured Logging

- **config/logging_config.py**
  - Python logging: rotate files under `logs/`, format with timestamp, level, module. Optionally JSON lines for later parsing.

### 4.5 Real-Time PnL and Equity Curve (Optional)

- Script or small dashboard (e.g. Streamlit or Grafana + Prometheus): read from Supabase `trade_log` and Alpaca positions to show equity curve and daily PnL. Manual: run backtests and record equity curve to CSV/DB for comparison.

---

## Phase 5: Backtesting, Walk-Forward, and Monte Carlo

**Goal:** Prove the strategy logic on historical crises (2008, 2020, 2022) and avoid curve fitting.

### 5.1 Backtesting Engine (Vectorized or Event-Driven)

- **backtesting/engine.py**
  - Input: OHLCV DataFrame, list of signals (date, symbol, side, qty or notional). Assume fill at close of signal bar; apply a simple slippage model (e.g. 0.1%).
  - Output: equity curve, total return, max drawdown, win rate, Sharpe (annualized).

### 5.2 Signal Generation from Consensus Logic

- **backtesting/signal_from_agents.py**
  - For each date in history, run Researcher/Sentiment/Chartist with historical data up to that date (point-in-time). Risk Officer uses backtest equity. Consensus rule same as live. Produce list of (date, symbol, side, qty) for engine. Note: Gemini calls in backtest are expensive; consider caching or a simplified rule-based surrogate for large runs.

### 5.3 Walk-Forward Optimization

- **backtesting/walk_forward.py**
  - Train window (e.g. 252 days) and test window (e.g. 63 days). Roll forward; for each test window run backtest. Report out-of-sample metrics (return, max DD, Sharpe) to avoid curve fitting.

### 5.4 Monte Carlo (Path Dependency)

- **backtesting/monte_carlo.py**
  - Reshuffle returns or bootstrap trade PnL series; run 1000+ paths. Report distribution of max drawdown and failure rate (e.g. % of paths exceeding 1.5% daily DD).

### 5.5 RegimeTest (Audit: Backtest Stress)

- **backtesting/regime_test.py**
  - **Mandatory two regimes:** (1) **2022 Tech Bear Market:** date range e.g. 2022-01-01 to 2022-12-31; run backtest; document max drawdown, circuit-breaker behavior. (2) **August 2024 Volatility Spike:** e.g. 2024-08-01 to 2024-08-31; same. Output: report (max_dd, sharpe, win_rate, regime name). **Bot must be tested against these two regimes before production.**

### 5.6 Manual Steps

- Run backtest on 2008, 2020, 2022 slices; document max drawdown and circuit breaker behavior.
- **Run RegimeTest** for 2022 Tech Bear and August 2024 Volatility; document in README or report. Confirm bot survives (or document limits).
- Run walk-forward and Monte Carlo; document results.

---

## Phase 6: Hardening and Production Readiness

**Goal:** Kill-switch, fat-finger/API error handling, failover, and production checklist.

### 6.1 Kill-Switch and Circuit Breaker

- **risk/kill_switch.py**
  - Global kill-switch: env var or file flag `TRADING_ENABLED=false` to disable all order submission. Check at start of Executor. Circuit breaker from Phase 3 must also prevent new trades when daily DD >= 1.5%.

### 6.2 API and Fat-Finger Handling

- **execution/alpaca_client.py** (extend)
  - Validate order size and symbol format before submit. Catch Alpaca API exceptions; log and retry with backoff for transient errors; never retry market order blindly (idempotency). Alerts on repeated failures (log or optional webhook).

### 6.3 Failover and Redundancy (Optional)

- If running 24/7: process supervisor (e.g. systemd or Docker restart policy). Optional: secondary data source (e.g. Polygon or other provider if Alpaca data fails) behind a thin abstraction.

### 6.4 Pre-Real-Money Checklist (Manual)

- All API keys for production Alpaca (live) set only when switching from paper; double-check `APCA_API_BASE_URL` for live vs paper.
- Backtest, walk-forward, Monte Carlo, and **RegimeTest** (2022 Tech Bear + Aug 2024 Volatility) reviewed; 1.5% daily DD and 1% per-trade risk enforced; post_mortem flow tested.
- DataValidator and smart_limit_order verified; kill-switch and circuit breaker tested.
- Logging and Supabase writes verified; no sensitive data in logs.
- Start with minimum position sizes in live; monitor for at least one week.

---

## Audit Compliance Summary


| Requirement             | Where Implemented                                                                                                  |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Model Hybridization** | Researcher: gemini-3.1-pro-preview; Sentiment & Chartist: gemini-3-flash-preview (Phase 2; config)                 |
| **Smart Limit Order**   | `smart_limit_order(symbol, side, qty, 60)` at mid-price, 60s expiration (Phase 1.6, 3.1)                           |
| **Data Sanity Check**   | `utils/data_validator.py` — two price sources (e.g. bars vs quote) within 0.1% before every trade (Phase 1.5, 3.1) |
| **Async Orchestration** | `orchestration/consensus.py` — `asyncio.gather` for Researcher, Sentiment, Chartist (Phase 2.6)                    |
| **RegimeTest**          | `backtesting/regime_test.py` — 2022 Tech Bear + August 2024 Volatility Spike (Phase 5.5)                           |
| **Recovery Protocol**   | On 1.5% DD: `write_post_mortem(failure_state)` to Supabase `post_mortem` (Phase 3.2, 4.1)                          |


## Deliverables Summary (Refactored)


| Phase | Deliverable                                                                                                                        |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 0     | Venv, requirements, config (Pro/Flash model names), folder skeleton including `utils/`, .env                                       |
| 1     | Alpaca data connector + latest price, news feed, Gemini analyst (Pro), DataValidator, smart_limit_order (mid, 60s), Phase 1 script |
| 2     | Researcher (Pro), Sentiment (Flash), Chartist (Flash), Risk Officer; Kelly; **async** consensus with asyncio.gather                |
| 3     | Executor (smart_limit_order + DataValidator); circuit breaker + **post_mortem** write to Supabase                                  |
| 4     | Supabase schema including **post_mortem**; client; Redis optional; logging                                                         |
| 5     | Backtest engine, signal generation, walk-forward, Monte Carlo, **RegimeTest** (2022 + Aug 2024)                                    |
| 6     | Kill-switch, API error handling, production checklist                                                                              |


---

## Optional: Exporting This Plan to Files

After you approve this plan, you can ask to export it into:

- **Option A:** One file: `DINETRADE_MASTER_PLAN.md` containing the full text above.
- **Option B:** Three files: `PLAN_Phase0_Phase1.md`, `PLAN_Phase2_Phase3_Phase4.md`, `PLAN_Phase5_Phase6_Manual.md` for phased execution and checklist ticking.

No code or environment changes have been made; this is planning only. Proceed to implementation phase by phase and run manual verification steps as indicated.