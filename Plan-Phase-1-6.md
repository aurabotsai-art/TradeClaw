# DineTrade: Production-Grade Plan (Phases 1–6) — Audit Refactor

**Strict Audit Requirements Applied:** Model Hybridization, Smart Limit Execution, Data Sanity Check, Async Orchestration, RegimeTest, Recovery Protocol.

---

## Refactored Project Structure

Execute in project root: `c:\Users\muham\Downloads\trade bot`

```text
dine_trade/
  __init__.py
  config/
    __init__.py
    settings.py          # GEMINI_MODEL_RESEARCHER, GEMINI_MODEL_FAST
  data/
    __init__.py
    connectors/
      __init__.py
      openbb_connector.py
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
    data_validator.py    # OpenBB vs Alpaca price within 0.1%
  backtesting/
    __init__.py
    engine.py
    signal_from_agents.py
    walk_forward.py
    monte_carlo.py
    regime_test.py       # 2022 Tech Bear, Aug 2024 Volatility
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

**Config additions (config/settings.py):**
- `GEMINI_MODEL_RESEARCHER = "gemini-3.1-pro-preview"`
- `GEMINI_MODEL_FAST = "gemini-3-flash-preview"` (used for Sentiment + Chartist)

---

## Phase 1: The 48-Hour Paper Skeleton (Production-Grade)

**Goal:** Data Connector → Gemini Analyst → **DataValidator** → **Smart limit order** (mid-price, 60s) on Alpaca paper. No multi-agent yet.

### 1.1 Data Connector (OpenBB)

- **data/connectors/openbb_connector.py**
  - `get_ohlcv(symbol: str, days: int = 100) -> pd.DataFrame`: OpenBB equity history; columns `date`, `open`, `high`, `low`, `close`, `volume`.
  - **Add:** `get_latest_price(symbol: str) -> float`: return latest close (or last available price) for use in DataValidator.
  - Handle missing OpenBB token via env.
  - **Manual:** Verify NVDA 100-day fetch and `get_latest_price` return.

### 1.2 News Headlines (Minimal)

- **data/feeds/news_feed.py**
  - `get_recent_headlines(symbol: str, limit: int = 10) -> list[dict]`: FMP/NewsAPI; keys `title`, `published_at`, `source`.

### 1.3 Gemini Analyst (Conviction Score)

- **agents/analyst/gemini_analyst.py**
  - For Phase 1 single analyst: use **gemini-3.1-pro-preview** (from `GEMINI_MODEL_RESEARCHER`) for consistency with future Researcher agent.
  - `get_conviction_score(ohlcv_df, headlines, symbol) -> tuple[float, str]`: build OHLCV summary + headlines; prompt for SCORE 1–10 and REASONING; parse and return `(score, reasoning)`.

### 1.4 Hard-Coded Safety Constraint (Anti-Hallucination)

- **risk/limits.py**
  - `price_vs_ma_allowed(price, ma20, max_deviation_pct=5.0) -> bool`: allow only if price within 5% of 20-day MA.

### 1.5 DataValidator (Audit: Data Sanity Check)

- **utils/data_validator.py**
  - **Required before any trade.**
  - `validate_price_agreement(openbb_price: float, alpaca_price: float, tolerance_pct: float = 0.1) -> tuple[bool, str]`:
    - Compute deviation = `abs(openbb_price - alpaca_price) / alpaca_price * 100`.
    - Return `(True, "OK")` if deviation <= 0.1%; else `(False, f"Price deviation {deviation:.4f}% exceeds 0.1%")`.
  - Used in Phase 1 script and in Executor (Phase 3) before every order.

### 1.6 Execution: Smart Limit Order (Audit: Replace Market Buy)

- **execution/alpaca_client.py**
  - **Remove:** `submit_market_buy` as the primary execution path.
  - **Add:** `get_latest_quote(symbol: str) -> dict`: Alpaca API (e.g. `get_latest_quote(symbol)`) return `{"bid": float, "ask": float}`.
  - **Add:** `smart_limit_order(symbol: str, side: str, qty: float, time_in_force_sec: int = 60) -> dict`:
    - Call `get_latest_quote(symbol)`. Compute **mid_price = (bid + ask) / 2**.
    - Submit **limit order** at `mid_price`, side `buy` or `sell`, qty, and **time_in_force** set to **60 seconds** (e.g. Alpaca `time_in_force="day"` with cancel-after logic, or use a 60s IOC-style if supported; otherwise implement: submit limit, schedule cancel after 60s). Document: "Limit at mid with 60s expiration."
    - Return order response (order_id, status).
  - Keep `get_account() -> dict`.

### 1.7 Phase 1 Orchestration Script

- **scripts/run_paper_phase1.py**
  - Fetch OHLCV (OpenBB) and headlines; compute 20-day MA and `price_vs_ma_allowed`.
  - Call Gemini analyst `get_conviction_score`.
  - **Before any order:** Get OpenBB latest price and Alpaca live price (from quote mid or last trade). Call `DataValidator.validate_price_agreement(openbb_price, alpaca_price, 0.1)`. If not valid, **abort and log**; do not send order.
  - If score > 8 and MA constraint and DataValidator pass: call **`smart_limit_order("NVDA", "buy", qty, 60)`** (fixed small qty). Else log reason.
  - Log conviction, reasoning, and order result to console and `logs/phase1_YYYYMMDD.log`.

### 1.8 Manual Verification

- Run script; confirm data load, Gemini score, **DataValidator pass/fail**, and **limit order at mid with 60s** on Alpaca paper dashboard.
- Intentionally use a stale OpenBB price or mock 0.2% divergence and confirm order is aborted.

---

## Phase 2: Multi-Agent Foundation (Model Hybridization + Async)

**Goal:** Four specialist agents with **model split**; **async parallel** orchestration; no execution yet.

### 2.1 Researcher Agent (Fundamental) — Gemini 1.5 Pro Only

- **agents/researcher/agent.py**
  - **Model:** Use **gemini-3.1-pro-preview** (config: `GEMINI_MODEL_RESEARCHER`).
  - Inputs: `symbol`, optional `ohlcv_df`, fundamental dict from OpenBB (P/E, Debt/Equity), SEC filing context.
  - Prompt: "As a Fundamental Researcher, given this company data and SEC context for {symbol}, output VERDICT: APPROVE or REJECT, SCORE 1-10, and brief reasoning."
  - Return: `{"verdict": "APPROVE"|"REJECT", "score": float, "reasoning": str}`.

### 2.2 Sentiment Agent (Newsroom) — Gemini 1.5 Flash

- **agents/sentiment/agent.py**
  - **Model:** Use **gemini-3-flash-preview** (config: `GEMINI_MODEL_FAST`) for high-speed sentiment.
  - Inputs: `symbol`, `headlines`.
  - Prompt: "As a Sentiment Analyst, score news sentiment for {symbol} 1-10. Output VERDICT: APPROVE or REJECT, SCORE, brief reasoning."
  - Return: same structure.

### 2.3 Chartist Agent (Technical) — Gemini 1.5 Flash

- **agents/chartist/agent.py**
  - **Model:** Use **gemini-3-flash-preview** (config: `GEMINI_MODEL_FAST`) for high-speed technical analysis.
  - Inputs: `symbol`, `ohlcv_df`. Compute RSI(14), MACD(12,26,9), 20/50 MAs, pattern labels.
  - Prompt: "As a Technical Chartist, given these indicators for {symbol}, output VERDICT: APPROVE or REJECT, SCORE 1-10, brief reasoning."
  - Return: same structure.

### 2.4 Risk Officer Agent

- **agents/risk_officer/agent.py**
  - Inputs: `symbol`, `price`, `account_equity`, `position_size_usd` or `qty`, optional `volatility` (ATR).
  - Enforce: max risk 1% per trade; fractional Kelly; daily drawdown >= 1.5% → REJECT.
  - Return: `{"verdict": "APPROVE"|"REJECT", "max_qty": float, "reasoning": str}`.

### 2.5 Kelly and Position Sizing

- **risk/kelly.py**
  - `kelly_fraction(win_rate, avg_win, avg_loss) -> float`
  - `position_size_cap(equity, risk_pct, volatility, kelly_f) -> float`

### 2.6 Orchestration — Async Parallel (Audit: asyncio.gather)

- **orchestration/consensus.py**
  - **Refactor to async.** Input: `symbol`, `account_equity`, `positions`, `ohlcv_df`, `headlines`.
  - Run **Researcher, Sentiment, Chartist in parallel** using **`asyncio.gather(researcher_task(), sentiment_task(), chartist_task())`**. Each agent must be callable as async (use `asyncio.to_thread` for sync Gemini calls if needed, or use async Gemini client).
  - After all three complete, run **Risk Officer** (depends on equity/positions; can be sync or async).
  - Consensus rule: Execute only if all three return APPROVE, score threshold (e.g. >= 7), and Risk Officer APPROVE.
  - Output: `{"approved": bool, "reason": str, "suggested_qty": float, "agent_results": dict}`.

### 2.7 Manual Steps

- Unit test each agent with mock data; confirm model names (Pro vs Flash) in config and in code.
- Run async orchestration for NVDA; log consensus and timings to verify parallel execution.

---

## Phase 3: Risk-First Executor, Smart Limit, Recovery Protocol

**Goal:** Executor uses **smart_limit_order** only; **DataValidator** before every order; on 1.5% DD trigger **post_mortem** to Supabase.

### 3.1 Executor Agent

- **agents/executor/agent.py**
  - Input: consensus (`approved`, `suggested_qty`, `symbol`), current price sources (OpenBB + Alpaca).
  - If not `approved`: return without order.
  - **Data sanity:** Call `DataValidator.validate_price_agreement(openbb_price, alpaca_price, 0.1)`. If not valid, **abort and log**; do not send order.
  - Re-check Risk Officer rules (daily drawdown, position size) immediately before order.
  - Call **`smart_limit_order(symbol, "buy", qty, 60)`** (qty capped by Risk’s `max_qty`). No market orders.
  - Return order_id and status.

### 3.2 Daily Drawdown Circuit Breaker + Recovery Protocol (Audit)

- **risk/limits.py**
  - Record `equity_at_open` at start of day. Before every trade: `current_equity`; drawdown_pct = `(equity_at_open - current_equity) / equity_at_open * 100`.
  - If drawdown_pct >= 1.5%:
    - Set circuit breaker; block all new trades.
    - **Recovery Protocol:** Call **post_mortem handler** (see below). Do not just stop silently.

- **storage/post_mortem.py** (new) or extend **storage/supabase_client.py**
  - **write_post_mortem(failure_state: dict) -> None**
  - `failure_state` must include: `triggered_at` (timestamp), `equity_at_open`, `current_equity`, `drawdown_pct`, **positions_snapshot** (current positions from Alpaca), **sentiment_snapshot** (last Sentiment agent output or headlines), **charts_snapshot** (last Chartist output or key technicals). Optionally: `agent_summary` (all four agent verdicts/reasoning).
  - Insert into Supabase table **`post_mortem`** (see Phase 4.1).

### 3.3 Trade and State Logging

- **storage/trade_logger.py**
  - Log every trade attempt (symbol, qty, side, limit price, consensus summary, timestamp) to file and Supabase `trade_log`.

### 3.4 Wiring Full Pipeline

- **scripts/run_consensus_trade.py**
  - Load config; fetch OHLCV and headlines; get account equity; run **async** orchestration; then Executor if approved (with DataValidator and smart_limit_order); on circuit breaker trigger, call `write_post_mortem(...)` then exit or pause.

### 3.5 Manual Steps

- Run end-to-end paper; trigger a limit order when conditions met; verify 60s limit on Alpaca.
- Simulate 1.5% daily drawdown (e.g. mock equity drop); confirm circuit breaker fires and **post_mortem** row appears in Supabase with positions, sentiment, and charts snapshots.

---

## Phase 4: Data Layer, Logging, Post-Mortem Schema

**Goal:** Supabase with **post_mortem** table; Redis optional; structured logging.

### 4.1 Supabase Schema

- **Manual:** In Supabase SQL editor, create:
  - **trade_log:** id (uuid), symbol, side, qty, price, order_id, alpaca_order_id, consensus_snapshot (jsonb), created_at, strategy_phase.
  - **daily_state:** date (date), equity_at_open, circuit_breaker_fired (boolean), updated_at.
  - **agent_runs:** id, run_id, agent_name, symbol, verdict, score, reasoning, created_at.
  - **post_mortem** (Audit: Recovery Protocol):
    - id (uuid), triggered_at (timestamptz), equity_at_open (numeric), current_equity (numeric), drawdown_pct (numeric), positions_snapshot (jsonb), sentiment_snapshot (jsonb), charts_snapshot (jsonb), agent_summary (jsonb), created_at (timestamptz).

### 4.2 Supabase Client

- **storage/supabase_client.py**
  - Insert `trade_log`, upsert `daily_state`, insert `agent_runs`, **insert `post_mortem`** (used by `write_post_mortem`).

### 4.3 Redis (Optional)

- **storage/redis_client.py**
  - Store equity_at_open, circuit_breaker, last_trade_time; TTL 24h.

### 4.4 Structured Logging

- **config/logging_config.py**
  - Rotate files under `logs/`, timestamp, level, module; optional JSON lines.

### 4.5 Real-Time PnL / Dashboard (Optional)

- Script or Streamlit/Grafana: read `trade_log` and Alpaca positions; optional view of `post_mortem` for post-incident review.

---

## Phase 5: Backtesting, Walk-Forward, Monte Carlo, RegimeTest (Audit)

**Goal:** Backtest engine, walk-forward, Monte Carlo, plus **mandatory RegimeTest** for 2022 Tech Bear and August 2024 Volatility Spike.

### 5.1 Backtesting Engine

- **backtesting/engine.py**
  - Input: OHLCV DataFrame, signals (date, symbol, side, qty). Fill at close; slippage (e.g. 0.1%).
  - Output: equity curve, total return, max drawdown, win rate, Sharpe (annualized).

### 5.2 Signal Generation from Consensus Logic

- **backtesting/signal_from_agents.py**
  - Point-in-time run of agents (or cached/surrogate); produce (date, symbol, side, qty) for engine.

### 5.3 Walk-Forward Optimization

- **backtesting/walk_forward.py**
  - Train 252d, test 63d; roll forward; report out-of-sample return, max DD, Sharpe.

### 5.4 Monte Carlo (Path Dependency)

- **backtesting/monte_carlo.py**
  - Bootstrap/reshuffle returns; 1000+ paths; distribution of max drawdown and % paths exceeding 1.5% daily DD.

### 5.5 RegimeTest (Audit: Backtest Stress)

- **backtesting/regime_test.py**
  - **Mandatory two regimes:**
    1. **2022 Tech Bear Market:** Define date range (e.g. 2022-01-01 to 2022-12-31 or subset). Run backtest over this period; document max drawdown, number of circuit-breaker triggers (if simulated), and that strategy survives within 1.5% daily DD logic.
    2. **August 2024 Volatility Spike:** Define date range (e.g. 2024-08-01 to 2024-08-31). Same: run backtest; document max drawdown and circuit-breaker behavior.
  - Output: report or logged metrics (max_dd, sharpe, win_rate, regime name) for each regime. **Bot must be tested against these two regimes before production.**

### 5.6 Manual Steps

- Run backtest on 2008, 2020, 2022 slices; document results.
- **Run RegimeTest** for 2022 Tech Bear and August 2024 Volatility; document in README or report. Confirm bot survives (or document limits).

---

## Phase 6: Hardening and Production Readiness

**Goal:** Kill-switch, API/fat-finger handling, failover; production checklist.

### 6.1 Kill-Switch and Circuit Breaker

- **risk/kill_switch.py**
  - `TRADING_ENABLED=false` (env or file) disables all order submission. Check at start of Executor. Circuit breaker (1.5% DD) already triggers post_mortem and blocks trades (Phase 3).

### 6.2 API and Fat-Finger Handling

- **execution/alpaca_client.py**
  - Validate symbol and order size before submit. Catch Alpaca exceptions; retry with backoff for transient errors only; do not blindly retry limit orders (idempotency). Log repeated failures.

### 6.3 Failover (Optional)

- Process supervisor (systemd/Docker); optional secondary data source (Polygon if OpenBB fails).

### 6.4 Pre-Real-Money Checklist (Manual)

- Paper vs live base URL confirmed; backtest, walk-forward, Monte Carlo, **RegimeTest** (2022 + Aug 2024) reviewed.
- 1.5% daily DD and post_mortem flow tested; DataValidator and smart_limit_order verified; kill-switch tested.
- Start with minimum size in live; monitor one week.

---

## Audit Compliance Summary

| Requirement | Where Implemented |
|-------------|-------------------|
| **Model Hybridization** | Researcher: gemini-3.1-pro-preview; Sentiment & Chartist: gemini-3-flash-preview (Phase 2; config) |
| **Smart Limit Order** | `smart_limit_order(symbol, side, qty, 60)` at mid-price, 60s expiration (Phase 1.6, 3.1) |
| **Data Sanity Check** | `utils/data_validator.py` — OpenBB vs Alpaca within 0.1% before every trade (Phase 1.5, 3.1) |
| **Async Orchestration** | `orchestration/consensus.py` — `asyncio.gather` for Researcher, Sentiment, Chartist (Phase 2.6) |
| **RegimeTest** | `backtesting/regime_test.py` — 2022 Tech Bear + August 2024 Volatility Spike (Phase 5.5) |
| **Recovery Protocol** | On 1.5% DD: `write_post_mortem(failure_state)` to Supabase `post_mortem` (Phase 3.2, 4.1) |

---

## Deliverables Summary (Refactored)

| Phase | Deliverable |
|-------|-------------|
| 0 | Venv, requirements, config (Pro/Flash model names), folder skeleton including `utils/`, .env |
| 1 | OpenBB connector + latest price, news feed, Gemini analyst (Pro), DataValidator, smart_limit_order (mid, 60s), Phase 1 script |
| 2 | Researcher (Pro), Sentiment (Flash), Chartist (Flash), Risk Officer; Kelly; **async** consensus with asyncio.gather |
| 3 | Executor (smart_limit_order + DataValidator); circuit breaker + **post_mortem** write to Supabase |
| 4 | Supabase schema including **post_mortem**; client; Redis optional; logging |
| 5 | Backtest engine, signal generation, walk-forward, Monte Carlo, **RegimeTest** (2022 + Aug 2024) |
| 6 | Kill-switch, API error handling, production checklist |
