---
name: ""
overview: ""
todos: []
isProject: false
---

# DineTrade: Complete Master Build Plan V2.0

### Production-Grade | Self-Evolving | Multi-Asset | Live Data | Full Intelligence Stack

**Status:** Expanded from V1 (Phase 0–6) → V2 (Phase 0–14)  
**Additions:** Live streaming data, crypto/forex, advanced execution, vector DB, deployment, monitoring, self-evolution  
**Model Fix:** `gemini-3.1-pro-preview` (Researcher), `gemini-3-flash-preview` (Sentiment + Chartist)

---

## ⚠️ AUDIT: What V1 Was Missing


| Gap                           | Status in V1         | Fixed In    |
| ----------------------------- | -------------------- | ----------- |
| Live news WebSocket stream    | ❌ Polling only       | Phase 7     |
| Real-time tick/quote stream   | ❌ REST batch only    | Phase 7     |
| Crypto (Binance)              | ❌ Not covered        | Phase 8     |
| Forex (OANDA)                 | ❌ Not covered        | Phase 8     |
| TWAP/VWAP execution           | ❌ Missing            | Phase 9     |
| Order book imbalance          | ❌ Missing            | Phase 9     |
| Iceberg/hidden orders         | ❌ Missing            | Phase 9     |
| Dark pool / whale monitoring  | ❌ Missing            | Phase 10    |
| Vector DB (Pinecone/Milvus)   | ❌ Missing            | Phase 10    |
| Earnings call audio sentiment | ❌ Missing            | Phase 10    |
| SEC EDGAR real-time watcher   | ❌ Missing            | Phase 10    |
| Grafana/Prometheus dashboard  | ❌ Missing            | Phase 11    |
| Market scheduler / cron       | ❌ Missing            | Phase 12    |
| Cloud deployment (AWS/GCP)    | ❌ Missing            | Phase 12    |
| C++/Rust latency layer        | ❌ Missing            | Phase 13    |
| Self-evolution / auto-retrain | ❌ Missing            | Phase 14    |
| Wrong Gemini model names      | ❌ gemini-3.x-preview | Fixed below |


---

## Phase 0: Prerequisites and Environment Setup ✅ (FROM V1 — CORRECTED)

**Goal:** Reproducible Python 3.12+ environment, API keys, folder skeleton.

### 0.1 API Keys and Accounts

- **Google AI (Gemini):** `aistudio.google.com` → `GEMINI_API_KEY`
- **Alpaca (Equities):** `alpaca.markets` → `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, `APCA_API_BASE_URL=https://paper-api.alpaca.markets`
- **Binance (Crypto):** `binance.com` → `BINANCE_API_KEY`, `BINANCE_SECRET_KEY` (use testnet first)
- **OANDA (Forex):** `oanda.com` → `OANDA_API_KEY`, `OANDA_ACCOUNT_ID` (practice account first)
- **Polygon.io:** `polygon.io` → `POLYGON_API_KEY` (WebSocket + REST)
- **Financial Modeling Prep:** `financialmodelingprep.com` → `FMP_API_KEY`
- **Alpaca News WebSocket:** Included with Alpaca account (free tier)
- **Supabase:** `supabase.com` → `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- **Redis:** Docker local or Upstash → `REDIS_URL`
- **Pinecone:** `pinecone.io` → `PINECONE_API_KEY`, `PINECONE_ENV` (vector DB for financial history)
- **SEC EDGAR:** Free, no key needed → `EDGAR_USER_AGENT` (your email for compliance)

### 0.2 Full Project Skeleton

```text
dine_trade/
  __init__.py
  config/
    settings.py          # All env vars + constants
    logging_config.py
  data/
    connectors/
      alpaca_connector.py      # Equities REST
      alpaca_ws_connector.py   # Equities WebSocket (NEW Phase 7)
      binance_connector.py     # Crypto REST (NEW Phase 8)
      binance_ws_connector.py  # Crypto WebSocket (NEW Phase 8)
      oanda_connector.py       # Forex REST (NEW Phase 8)
      polygon_ws_connector.py  # Level 2 / tick stream (NEW Phase 7)
    feeds/
      news_feed.py             # FMP/NewsAPI polling (Phase 1)
      alpaca_news_ws.py        # Live news WebSocket (NEW Phase 7)
      sec_edgar_watcher.py     # Real-time SEC filings (NEW Phase 10)
      earnings_audio.py        # Earnings call audio sentiment (NEW Phase 10)
      darkpool_feed.py         # Dark pool / whale flow (NEW Phase 10)
  agents/
    analyst/
      gemini_analyst.py        # Phase 1 single analyst
    researcher/
      agent.py                 # gemini-3.1-pro-preview ONLY
    sentiment/
      agent.py                 # gemini-3-flash-preview
    chartist/
      agent.py                 # gemini-3-flash-preview
    risk_officer/
      agent.py
    executor/
      agent.py
    macro_monitor/
      agent.py                 # NEW Phase 10: geopolitical tracking
  orchestration/
    consensus.py               # asyncio.gather parallel agents
    regime_detector.py         # NEW Phase 9: trend vs. range
  execution/
    alpaca_client.py           # smart_limit_order (mid-price, 60s)
    twap_executor.py           # NEW Phase 9: TWAP algo
    vwap_executor.py           # NEW Phase 9: VWAP algo
    iceberg_order.py           # NEW Phase 9: iceberg/hidden
    sor.py                     # NEW Phase 9: Smart Order Routing
    binance_executor.py        # NEW Phase 8: crypto execution
    oanda_executor.py          # NEW Phase 8: forex execution
  storage/
    supabase_client.py
    redis_client.py
    vector_db.py               # NEW Phase 10: Pinecone/Milvus
    trade_logger.py
    post_mortem.py
  risk/
    limits.py
    kelly.py
    kill_switch.py
    atm_stop_loss.py           # NEW Phase 9: dynamic ATR stops
    correlation_limits.py      # NEW Phase 9: cross-asset exposure
    black_swan.py              # NEW Phase 9: kill-switch protocols
    slippage_monitor.py        # NEW Phase 9: slippage/spread
  utils/
    data_validator.py
    feature_engineering.py     # NEW Phase 7: real-time features
    orderbook_imbalance.py     # NEW Phase 9: OBI detection
  backtesting/
    engine.py
    signal_from_agents.py
    walk_forward.py
    monte_carlo.py
    regime_test.py
  monitoring/
    prometheus_metrics.py      # NEW Phase 11
    grafana_dashboards/        # NEW Phase 11
    alerting.py                # NEW Phase 11
  deployment/
    scheduler.py               # NEW Phase 12: market hours cron
    docker/                    # NEW Phase 12
    infra/                     # NEW Phase 12: AWS/GCP IaC
  evolution/
    performance_tracker.py     # NEW Phase 14
    strategy_mutator.py        # NEW Phase 14
    auto_retrain.py            # NEW Phase 14
  logs/
  tests/
  scripts/
    run_paper_phase1.py
    run_consensus_trade.py
    run_live.py                # NEW Phase 12
  .env.example
  requirements.txt
  README.md
```

### 0.3 Corrected Model Names (CRITICAL FIX)

```python
# config/settings.py — CORRECTED from V1
GEMINI_MODEL_RESEARCHER = "gemini-3.1-pro-preview"        # NOT gemini-3.1-pro-preview
GEMINI_MODEL_FAST       = "gemini-3-flash-preview"       # NOT gemini-3-flash-preview

# When Gemini 2.0 is needed:
# GEMINI_MODEL_RESEARCHER = "gemini-2.0-pro-exp"
# GEMINI_MODEL_FAST       = "gemini-2.0-flash-exp"
```

### 0.4 Extended requirements.txt

```text
python-dotenv>=1.0.0
google-generativeai>=0.8.0
alpaca-trade-api>=3.0.0
alpaca-py>=0.13.0              # NEW: modern Alpaca SDK with WebSocket
requests>=2.31.0
pandas>=2.0.0
numpy>=1.24.0
supabase>=2.0.0
redis>=5.0.0
langgraph>=0.0.20
langchain-google-genai>=2.0.0
websocket-client>=1.6.0
python-binance>=1.0.19         # NEW: Binance crypto
oandapyV20>=0.7.0             # NEW: OANDA forex
pinecone-client>=3.0.0         # NEW: vector DB
ta>=0.11.0                     # NEW: technical analysis library
scipy>=1.11.0                  # NEW: stats for MC simulation
streamlit>=1.28.0              # NEW: dashboard
prometheus-client>=0.18.0      # NEW: metrics
asyncio>=3.4.3
aiohttp>=3.9.0
sec-edgar-downloader>=5.0.0    # NEW: SEC filings
pydub>=0.25.1                  # NEW: audio processing
openai-whisper>=20231117        # NEW: earnings audio transcription
```

---

## Phase 1: Paper Skeleton — Equities (FROM V1 — UNCHANGED)

**Goal:** Alpaca data → Gemini analyst → DataValidator → smart limit order on paper.

*(See V1 Phase 1 for full detail: sections 1.1–1.8)*

Key deliverables:

- `data/connectors/alpaca_connector.py` — REST OHLCV + latest price
- `data/feeds/news_feed.py` — FMP/NewsAPI headlines polling
- `agents/analyst/gemini_analyst.py` — conviction score with **gemini-3.1-pro-preview**
- `utils/data_validator.py` — dual price source ±0.1% tolerance
- `execution/alpaca_client.py` — `smart_limit_order(symbol, side, qty, 60s)`
- `scripts/run_paper_phase1.py`

---

## Phase 2: Multi-Agent Foundation (FROM V1 — MODEL NAMES CORRECTED)

**Goal:** Researcher / Sentiment / Chartist / Risk Officer with async consensus.

*(See V1 Phase 2 for full detail: sections 2.1–2.7)*

Key deliverables:

- `agents/researcher/agent.py` — **gemini-3.1-pro-preview** fundamental + SEC context
- `agents/sentiment/agent.py` — **gemini-3-flash-preview** news headlines
- `agents/chartist/agent.py` — **gemini-3-flash-preview** RSI/MACD/MA
- `agents/risk_officer/agent.py` — Kelly + 1% per-trade + 1.5% daily DD
- `orchestration/consensus.py` — `asyncio.gather` parallel
- `risk/kelly.py`

---

## Phase 3: Risk-First Executor + Recovery Protocol (FROM V1 — UNCHANGED)

**Goal:** Executor with DataValidator, smart_limit_order, post_mortem on DD breach.

*(See V1 Phase 3 for full detail: sections 3.1–3.5)*

Key deliverables:

- `agents/executor/agent.py` — full execution pipeline with all safety checks
- `risk/limits.py` — 1.5% daily drawdown circuit breaker
- `storage/post_mortem.py` — `write_post_mortem(failure_state)` to Supabase

---

## Phase 4: Data Layer, Logging, Observability (FROM V1 — UNCHANGED)

**Goal:** Supabase schema, Redis, structured logging, PnL tracking.

*(See V1 Phase 4 for full detail: sections 4.1–4.5)*

Key deliverables:

- Supabase tables: `trade_log`, `daily_state`, `agent_runs`, `post_mortem`
- `storage/supabase_client.py`, `storage/redis_client.py`
- `config/logging_config.py` — rotating JSON logs

---

## Phase 5: Backtesting, Walk-Forward, Monte Carlo (FROM V1 — UNCHANGED)

**Goal:** Prove strategy on historical crises. Mandatory RegimeTest.

*(See V1 Phase 5 for full detail: sections 5.1–5.6)*

Key deliverables:

- `backtesting/engine.py` — vectorized engine with slippage model
- `backtesting/walk_forward.py` — 252-day train / 63-day test rolling
- `backtesting/monte_carlo.py` — 1000+ path bootstrap
- `backtesting/regime_test.py` — **2022 Tech Bear + Aug 2024 Volatility** (mandatory)

---

## Phase 6: Hardening and Production Readiness (FROM V1 — UNCHANGED)

**Goal:** Kill-switch, fat-finger handling, failover, pre-live checklist.

*(See V1 Phase 6 for full detail: sections 6.1–6.4)*

Key deliverables:

- `risk/kill_switch.py` — env flag `TRADING_ENABLED=false`
- `execution/alpaca_client.py` — fat-finger validation, retry with backoff
- Pre-real-money checklist — all RegimeTests pass, DataValidator verified

---

---

# ██████ NEW PHASES — V2 EXPANSION ██████

---

## Phase 7: Live Data Streaming Infrastructure 🔴 NEW

**Goal:** Replace all polling with real-time WebSocket streams for quotes, trades, and news. This is the heartbeat of a professional trading system.

### 7.1 Alpaca WebSocket — Live Quotes and Trades

- **data/connectors/alpaca_ws_connector.py**
  - Use `alpaca-py` WebSocket client (`StockDataStream`)
  - Subscribe to: real-time quotes (`q`), trades (`t`), minute bars (`b`) for universe symbols
  - Handler pattern:

```python
    from alpaca.data.live import StockDataStream
    
    wss_client = StockDataStream(API_KEY, SECRET_KEY)
    
    async def quote_handler(data):
        # push to Redis stream: RPUSH quotes:NVDA data
        await redis.rpush(f"quotes:{data.symbol}", data.json())
    
    wss_client.subscribe_quotes(quote_handler, "NVDA", "AAPL")
    await wss_client.run()
    

```

- All incoming data published to Redis streams for consumption by agents
- Reconnect logic: exponential backoff, max 5 retries, alert on failure

### 7.2 Alpaca News WebSocket — Live News Stream 🔴 CRITICAL

- **data/feeds/alpaca_news_ws.py**
  - Use `alpaca-py` `NewsDataStream` (free with Alpaca account — no extra cost)
  - Subscribe to `*` (all news) or per-symbol
  - Handler:

```python
    from alpaca.data.live import NewsDataStream
    
    news_client = NewsDataStream(API_KEY, SECRET_KEY)
    
    async def news_handler(news):
        # news.headline, news.summary, news.symbols, news.created_at
        await redis.rpush("news:live", news.json())
        # Trigger Sentiment Agent if symbol in universe
        if any(s in UNIVERSE for s in news.symbols):
            await trigger_sentiment_rescan(news)
    
    news_client.subscribe_news(news_handler, *UNIVERSE)
    await news_client.run()
    

```

- This feeds the Sentiment Agent in **real-time** not on a schedule
- Store all news in Supabase `news_log` table with `(headline, symbols, sentiment_score, created_at)`

### 7.3 Polygon.io WebSocket — Level 2 Order Book 🔴 CRITICAL

- **data/connectors/polygon_ws_connector.py**
  - Connect to `wss://socket.polygon.io/stocks`
  - Subscribe to `Q.`* (quotes), `T.*` (trades), `A.*` (second aggregates)
  - For order book: subscribe to `LQ.*` (Level 2 NBBO quotes — requires Polygon Starter+)
  - Stream raw ticks to Redis: `ZADD ticks:{symbol} {timestamp} {data}`
  - Use this as second price source for DataValidator (replaces slower REST call)

### 7.4 Real-Time Feature Engineering

- **utils/feature_engineering.py**
  - Consumes from Redis streams, computes rolling features on incoming ticks:
    - `rolling_vwap(ticks, window_seconds)` — real-time VWAP
    - `rolling_rsi(closes, period=14)` — updated on each new bar
    - `bid_ask_spread(quote)` — monitors spread widening (liquidity warning)
    - `tick_velocity(ticks, window=60)` — trades-per-second spike detection
  - All features written back to Redis with TTL for fast agent consumption
  - Use `asyncio` pipeline — never block the main event loop

### 7.5 Data Stream Manager

- **data/stream_manager.py**
  - Master process that launches all WebSocket connections as async tasks
  - Health monitoring: if any stream drops, log + alert + reconnect
  - Graceful shutdown handler (SIGTERM/SIGINT → clean WebSocket close)

### 7.6 Manual Verification Steps

- Confirm Alpaca quote stream receiving NVDA ticks within 100ms
- Confirm Alpaca news stream fires within 5s of published headline
- Confirm Polygon Level 2 quotes updating in Redis
- Verify DataValidator can now use live quote stream instead of REST call
- Test reconnection: kill network for 30s, verify stream recovers

---

## Phase 8: Multi-Asset Expansion — Crypto and Forex 🔴 NEW

**Goal:** Extend the bot to trade Binance crypto and OANDA forex with the same multi-agent framework.

### 8.1 Binance Crypto Connector (REST)

- **data/connectors/binance_connector.py**
  - `get_ohlcv(symbol, interval="1h", limit=200) -> pd.DataFrame`
    - Uses `python-binance` `get_klines(symbol, interval, limit)`
    - Symbols format: `BTCUSDT`, `ETHUSDT`, `SOLUSDT`
  - `get_ticker(symbol) -> dict` — latest price, 24h volume, % change
  - `get_order_book(symbol, depth=20) -> dict` — bid/ask ladder
  - Universe config: `CRYPTO_UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]`

### 8.2 Binance WebSocket — Live Crypto Stream

- **data/connectors/binance_ws_connector.py**
  - Use `python-binance` `BinanceSocketManager`
  - Subscribe to: `trade` (tick trades), `kline_1m` (live candles), `depth` (order book)
  - Handler publishes to Redis: `RPUSH crypto:trades:BTCUSDT data`
  - Aggregate book imbalance:

```python
    bid_volume = sum(float(b[1]) for b in order_book["bids"][:10])
    ask_volume = sum(float(a[1]) for a in order_book["asks"][:10])
    imbalance_ratio = bid_volume / (bid_volume + ask_volume)
    # > 0.65 = buy pressure, < 0.35 = sell pressure
    

```

### 8.3 Binance Execution

- **execution/binance_executor.py**
  - `place_limit_order(symbol, side, quantity, price) -> dict`
  - `place_market_order(symbol, side, quantity) -> dict` — only for emergency closes
  - `cancel_order(symbol, order_id)` — cancel unfilled limit orders after timeout
  - `get_position(symbol) -> dict` — current holdings
  - Testnet mode: set `BINANCE_TESTNET=true` in env → use `https://testnet.binance.vision`
  - Fat-finger check: order size must be within 2% of current market price
  - All orders logged to Supabase `trade_log` with `asset_class="CRYPTO"`

### 8.4 OANDA Forex Connector (REST)

- **data/connectors/oanda_connector.py**
  - `get_ohlcv(instrument, granularity="H1", count=200) -> pd.DataFrame`
    - Instruments: `EUR_USD`, `GBP_USD`, `USD_JPY`, `XAU_USD` (gold)
  - `get_latest_price(instrument) -> dict` — bid/ask/mid
  - `get_account_summary() -> dict` — balance, margin used, NAV

### 8.5 OANDA Execution

- **execution/oanda_executor.py**
  - `place_limit_order(instrument, units, price, stop_loss, take_profit) -> dict`
  - Units: positive = buy, negative = sell
  - Always include `stopLossOnFill` and `takeProfitOnFill` in every order
  - Hedge ratio: `get_open_trades()` for rebalancing
  - Practice account: set `OANDA_ENVIRONMENT="practice"` in env

### 8.6 Multi-Asset Orchestration

- **orchestration/consensus.py** (extend)
  - Add `asset_class` parameter: `"EQUITY"`, `"CRYPTO"`, `"FOREX"`
  - Route data fetching to correct connector based on asset class
  - Crypto runs 24/7 (no market hours check); Forex runs Sun 5pm – Fri 5pm EST
  - Equity-only circuit breakers remain; crypto has separate 3% daily drawdown limit (higher volatility)

### 8.7 Cross-Asset Correlation Risk

- **risk/correlation_limits.py**
  - `compute_correlation_matrix(positions: dict) -> pd.DataFrame`
    - Pull 30-day returns for all open positions across asset classes
    - If any two positions correlation > 0.85: flag as over-correlated
  - `check_total_exposure(positions, equity) -> tuple[bool, str]`
    - Max 40% of capital in correlated cluster
    - Max 60% total capital deployed at once
  - Run correlation check before every new position

### 8.8 Manual Verification Steps

- Confirm Binance testnet order placement and cancellation
- Confirm OANDA practice account order fills and P&L tracking
- Test correlated position rejection: open BTCUSDT + ETHUSDT, verify limit triggers
- Confirm crypto WebSocket streams data on weekends

---

## Phase 9: Advanced Execution Engine 🔴 NEW

**Goal:** Institutional-grade execution — TWAP, VWAP, iceberg orders, Smart Order Routing, dynamic ATR stops, order flow signals.

### 9.1 TWAP Executor (Time-Weighted Average Price)

- **execution/twap_executor.py**
  - `twap_order(symbol, side, total_qty, duration_minutes, num_slices) -> list[dict]`
  - Logic:

```python
    slice_qty = total_qty / num_slices
    interval = (duration_minutes * 60) / num_slices
    for i in range(num_slices):
        await asyncio.sleep(interval)
        price = await get_mid_price(symbol)
        order = await smart_limit_order(symbol, side, slice_qty, tif=30)
        orders.append(order)
    

```

- Use case: large orders in equities to minimize market impact
- Log each slice to `trade_log` with `execution_algo="TWAP"` and `parent_order_id`

### 9.2 VWAP Executor (Volume-Weighted Average Price)

- **execution/vwap_executor.py**
  - `vwap_order(symbol, side, total_qty, duration_minutes) -> list[dict]`
  - Use real-time volume from WebSocket to weight each slice
  - Compute target participation rate (e.g. 10% of market volume per interval)
  - Larger slice when volume is high, smaller slice when volume is low
  - Compare achieved fill price vs benchmark VWAP — log slippage delta
  - Use case: momentum strategies where you want to track market volume

### 9.3 Iceberg / Hidden Order Management

- **execution/iceberg_order.py**
  - `iceberg_order(symbol, side, total_qty, visible_qty, price_tolerance_pct=0.05)`
  - Show only `visible_qty` to market; refill automatically as fills come in
  - Checks Alpaca's `extended_hours` support; warns if not supported on broker
  - On Binance: use `icebergQty` parameter natively in REST API
  - Use case: large crypto positions where showing full size moves the market

### 9.4 Smart Order Routing (SOR)

- **execution/sor.py**
  - `route_order(symbol, side, qty, asset_class) -> str`
  - Decision logic:
    - If equity: use Alpaca (best execution for retail)
    - If crypto: compare Binance spot vs Binance futures spread — route to tighter spread
    - If forex: OANDA for retail sizes; flag if spread > 3 pips
  - `compare_venues(symbol) -> dict` — bid/ask spread across available venues
  - Future extension: add Coinbase, Kraken for crypto routing

### 9.5 Dynamic ATR-Based Stop Loss

- **risk/atm_stop_loss.py**
  - `compute_atr(ohlcv_df, period=14) -> float` — Average True Range
  - `dynamic_stop_price(entry_price, side, atr, multiplier=2.0) -> float`
    - Long stop: `entry_price - (atr * multiplier)`
    - Short stop: `entry_price + (atr * multiplier)`
  - `trailing_stop(current_price, side, atr, best_price, multiplier=2.0) -> float`
    - Best price tracks the most favorable price seen since entry
    - Stop trails best price by `atr * multiplier`
  - Update trailing stop on every new price tick from WebSocket stream
  - When stop is hit: trigger market close order immediately (not limit)

### 9.6 Trailing Take-Profit Logic

- **risk/limits.py** (extend)
  - `trailing_take_profit(entry_price, side, target_r_multiple=2.0) -> dict`
    - Initial take profit at `entry + (risk * target_r_multiple)`
    - Once price hits 50% of target: lock in break-even stop
    - Once price hits target: trail stop at 50% of remaining gain
  - Use `R-multiple` framework: risk = stop distance; target = 2x or 3x risk

### 9.7 Order Book Imbalance Detection

- **utils/orderbook_imbalance.py**
  - `compute_obi(order_book: dict, depth=10) -> float`
    - `OBI = (bid_vol - ask_vol) / (bid_vol + ask_vol)` where vol is top N levels
    - Range: -1.0 (strong sell pressure) to +1.0 (strong buy pressure)
  - `obi_signal(obi: float, threshold=0.3) -> str`
    - `> 0.3` → `"BULLISH_PRESSURE"`
    - `< -0.3` → `"BEARISH_PRESSURE"`
    - else → `"NEUTRAL"`
  - Feed OBI to Chartist Agent as additional signal input
  - For crypto: uses Binance depth WebSocket; for equities: uses Polygon Level 2

### 9.8 Market Regime Classifier

- **orchestration/regime_detector.py**
  - `classify_regime(ohlcv_df: pd.DataFrame) -> str`
  - Uses combination of:
    - ADX > 25 AND price above 50MA → `"TRENDING_UP"`
    - ADX > 25 AND price below 50MA → `"TRENDING_DOWN"`
    - ADX < 20 AND price within Bollinger Bands → `"RANGING"`
    - VIX-equivalent > 30 (use VIXY or compute from options if available) → `"HIGH_VOLATILITY"`
  - Strategy routing based on regime:
    - Trending: use momentum signals, wider stops
    - Ranging: use mean reversion signals, tighter targets
    - High volatility: reduce position size by 50%, widen stops
  - Run regime check every 15 minutes, cache in Redis

### 9.9 Slippage and Spread Monitor

- **risk/slippage_monitor.py**
  - `record_fill(order_id, expected_price, fill_price, side) -> float`
    - Slippage = fill_price - expected_price (negative = better than expected)
  - `check_spread_health(symbol) -> bool`
    - Fetch current bid/ask spread; if spread > `SPREAD_MAX_BPS` config: block new orders
    - Default: 5 bps for equities, 10 bps for crypto, 3 pips for forex
  - Log all slippage to Supabase `slippage_log` table
  - Weekly slippage report to check execution quality over time

### 9.10 Fat-Finger and API Error Handling (Extend Phase 6)

- **execution/alpaca_client.py** (extend)
  - `validate_order(symbol, qty, price, side) -> tuple[bool, str]`
    - Price must be within 2% of last known market price
    - Qty must not exceed 5% of 30-day average daily volume
    - Symbol must be in approved universe list
  - Idempotency key for all orders (UUID stored in Redis, expires 60s)
  - On `HTTP 429` (rate limit): backoff 2s, retry max 3 times
  - On `HTTP 500+` (server error): cancel order attempt, log, alert
  - Webhook alert on 3+ consecutive failures: POST to Slack/Telegram

### 9.11 Manual Verification Steps

- Execute a 100-share TWAP order on Alpaca paper over 10 minutes; confirm 10 equal slices
- Confirm VWAP slice sizing varies with volume
- Force ATR stop hit in paper: enter position, move price to stop; confirm immediate close
- Confirm OBI signal fires on an order book snapshot with 70/30 bid/ask imbalance
- Test regime classifier on 2022 bear data: should output "TRENDING_DOWN"

---

## Phase 10: Intelligence Expansion — Advanced Data Sources 🔴 NEW

**Goal:** Whale tracking, SEC filings, earnings audio, geopolitical events, vector DB memory.

### 10.1 Dark Pool and Whale Flow Monitoring

- **data/feeds/darkpool_feed.py**
  - Dark pool detection sources:
    - **Unusual Whales API** (`unusualwhales.com`) or **Quiver Quant** (`quiverquant.com`) — track large off-exchange prints
    - FMP: `get_dark_pool_levels(symbol)` — major dark pool price clusters
  - `get_dark_pool_prints(symbol, lookback_hours=24) -> list[dict]`
    - Returns prints above 10,000 shares (configurable)
    - Fields: `price`, `volume`, `timestamp`, `venue`, `above_ask` (aggressor flag)
  - `detect_whale_accumulation(prints: list) -> dict`
    - Cluster prints by price level; if >3 large prints within 1% of each other → "ACCUMULATION" signal
  - Feed to Researcher Agent as contextual signal
  - Store whale prints in Supabase `whale_prints` table

### 10.2 SEC EDGAR Real-Time Watcher

- **data/feeds/sec_edgar_watcher.py**
  - Uses `sec-edgar-downloader` + EDGAR full-text search RSS feed
  - `watch_filings(symbols: list, form_types=["8-K", "10-K", "10-Q", "SC 13G", "SC 13D"])`
    - Polls EDGAR RSS every 5 minutes for new filings from watched companies
    - 8-K = material events (earnings, M&A, CEO change, etc.) — highest priority
    - SC 13G/D = institutional ownership changes (>5%) — whale tracking
  - `parse_filing_summary(filing_url) -> dict`
    - Downloads filing; extracts key sections using Gemini 3.1 Pro Preview
    - Prompt: "Extract: event type, financial impact, sentiment (positive/negative/neutral), any guidance changes"
    - Returns structured summary for Researcher Agent
  - On new 8-K: immediately trigger Researcher Agent rescan for that symbol
  - Store parsed summaries in Supabase `sec_filings` + embed in Pinecone (Phase 10.5)

### 10.3 Earnings Call Audio Sentiment

- **data/feeds/earnings_audio.py**
  - **Data source:** Seeking Alpha Earnings Call transcripts (scrape or API) or FMP transcripts endpoint
  - `get_earnings_transcript(symbol, quarter) -> str` — text of most recent call
  - `analyze_transcript_sentiment(transcript: str) -> dict`
    - Use Gemini 3.1 Pro Preview (long context window — 1M tokens handles entire transcript)
    - Prompt: "Analyze CEO tone, guidance sentiment (raised/lowered/maintained), mention of headwinds/tailwinds, confidence level 1-10, key phrases signaling concern"
    - Returns: `{tone, guidance_direction, confidence_score, red_flags, green_flags}`
  - **Audio-specific (optional):** If audio available (e.g. MP3 link):
    - Transcribe with OpenAI Whisper (`whisper.transcribe(audio_path)`)
    - Then pass transcript to Gemini for semantic analysis
    - Compare CEO voice tone patterns (hesitation, pace changes) — requires audio ML model
  - Store earnings analysis in Supabase `earnings_analysis`; embed in Pinecone

### 10.4 Geopolitical Macro Event Tracking

- **agents/macro_monitor/agent.py**
  - Tracks macro events that move all markets simultaneously
  - **Data sources:**
    - FRED API (Federal Reserve) — free, tracks: Fed Funds Rate, CPI, Unemployment
    - GDELT Project (global news events dataset) — free RSS
    - Economic calendar: FMP `get_economic_calendar()` for scheduled events (FOMC, CPI, NFP)
  - `get_upcoming_events(days_ahead=7) -> list[dict]`
    - Returns: Fed meeting, CPI release, NFP, earnings dates for universe symbols
    - Each event tagged with `volatility_impact`: "LOW", "MEDIUM", "HIGH", "EXTREME"
  - Pre-event risk reduction: if FOMC or CPI within 24 hours → Risk Officer reduces max position size by 50%
  - `assess_macro_regime() -> dict`
    - Queries recent FRED data: rate environment, inflation trend, employment trend
    - Returns: `{rate_env: "RISING"|"FALLING"|"FLAT", inflation_regime: ..., risk_off: bool}`
  - Feed macro regime to all agents as context header in every prompt

### 10.5 Vector Database for Financial Memory (Pinecone)

- **storage/vector_db.py**
  - `embed_text(text: str) -> list[float]` — use Gemini `embedding-001` model
  - `upsert_memory(id, text, metadata) -> None`
    - Stores: past trade reasoning, SEC filing summaries, news events, earnings analysis
    - Metadata: `{symbol, event_type, date, outcome, pnl}` for retrieval filtering
  - `query_similar(query_text, symbol=None, top_k=5) -> list[dict]`
    - Retrieve most relevant past events/reasoning for current situation
    - Filter by symbol and event type
  - Use in Researcher Agent: "Find similar past events to current situation and their outcomes"

```python
    context = vector_db.query_similar(
        f"Tech sector selloff during high inflation + rising rates {symbol}",
        symbol=symbol, top_k=3
    )
    # Inject context into Researcher prompt: "Historical analogues: {context}"
    

```

- Index namespaces: `filings`, `news_events`, `trade_reasoning`, `earnings`
- This gives the bot **memory** — it learns from every event it processes

### 10.6 Alpha Factor Research

- **backtesting/alpha_factors.py**
  - Systematic testing of quantitative signals for predictive power
  - Factors to test:
    - **Value:** P/E ratio below sector median
    - **Momentum:** 12-1 month price momentum (Fama-French)
    - **Quality:** ROE, gross margin stability
    - **Sentiment:** analyst revision momentum
    - **Technical:** 52-week high breakout
  - `compute_factor_ic(factor_values, forward_returns, horizon_days=5) -> float`
    - Information Coefficient (IC) — correlation of factor rank to future return
    - Target IC > 0.05 (statistically meaningful alpha)
  - `factor_decay_analysis(factor, max_days=20) -> pd.DataFrame`
    - How quickly does the factor's predictive power decay?
  - Top factors with IC > 0.05 are added to Chartist Agent signals

### 10.7 Manual Verification Steps

- Query EDGAR RSS for a symbol's recent filings; confirm 8-K detection within 5 min
- Parse an Apple earnings transcript with Gemini; confirm structured output
- Confirm Pinecone upsert and query returning relevant historical context
- Test macro event calendar: verify FOMC event triggers position size reduction
- Run alpha factor IC on 3 factors using 1 year of data; document results

---

## Phase 11: Monitoring, Alerting, and Dashboards 🔴 NEW

**Goal:** Professional-grade observability — Prometheus metrics, Grafana dashboards, real-time PnL, alerting.

### 11.1 Prometheus Metrics

- **monitoring/prometheus_metrics.py**
  - Expose metrics endpoint at `http://localhost:8000/metrics`
  - Key metrics to track:

```python
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
    
    trades_total = Counter("trades_total", "Total trades", ["symbol", "side", "asset_class"])
    pnl_gauge = Gauge("daily_pnl_usd", "Current day PnL in USD")
    drawdown_gauge = Gauge("current_drawdown_pct", "Current drawdown %")
    agent_latency = Histogram("agent_latency_seconds", "Agent response time", ["agent_name"])
    ws_reconnects = Counter("ws_reconnect_total", "WebSocket reconnection count", ["stream"])
    order_fill_rate = Gauge("order_fill_rate_pct", "% of limit orders that filled")
    slippage_avg = Gauge("avg_slippage_bps", "Average slippage in basis points")
    

```

- Run `start_http_server(8000)` at bot startup

### 11.2 Grafana Dashboard Setup

- **monitoring/grafana_dashboards/**
  - Dashboard 1: **Live Trading Dashboard**
    - Real-time PnL curve
    - Open positions table with entry price, current price, unrealized PnL
    - Daily drawdown % gauge with 1.5% red line
    - Orders placed (last 24h) timeline
  - Dashboard 2: **System Health Dashboard**
    - WebSocket stream status (green/red per stream)
    - Agent response times histogram
    - Redis queue depth
    - API call rate vs rate limits
  - Dashboard 3: **Risk Dashboard**
    - Correlation matrix heatmap (open positions)
    - Exposure by asset class pie chart
    - VaR (Value at Risk) estimate
    - Circuit breaker status
  - Dashboard 4: **Intelligence Dashboard**
    - Sentiment score trend per symbol (last 7 days)
    - News volume per symbol
    - Recent SEC filings flagged
    - Whale print alerts
  - Setup: Docker Compose with Prometheus + Grafana services

```yaml
    services:
      prometheus:
        image: prom/prometheus
        ports: ["9090:9090"]
      grafana:
        image: grafana/grafana
        ports: ["3000:3000"]
    

```

### 11.3 Real-Time PnL and Equity Curve

- **monitoring/pnl_tracker.py**
  - `compute_live_pnl(positions, current_prices) -> dict`
    - Realized PnL: from `trade_log` (closed trades)
    - Unrealized PnL: sum of (current_price - entry_price) * qty for open positions
    - Net PnL = realized + unrealized - commissions
  - Update every 30 seconds; push to Prometheus gauge
  - Store equity snapshots in Supabase `equity_curve` table (timestamp, equity, drawdown)
  - Compute Sharpe ratio daily: `(daily_return - risk_free_rate) / daily_return_std`

### 11.4 Alerting System

- **monitoring/alerting.py**
  - Alert channels: Telegram bot (easiest), Slack webhook, or email
  - Alert triggers:
    - Drawdown > 1.0% (warning) or > 1.5% (circuit breaker fired)
    - New position opened or closed
    - WebSocket stream down for > 60 seconds
    - API error rate > 5% in last 5 minutes
    - New 8-K SEC filing for any universe symbol
    - Whale print > $1M notional detected
    - Daily PnL > +3% (celebration) or < -1.5% (incident review trigger)
  - `send_alert(level, message, data) -> None`
    - Levels: INFO, WARNING, CRITICAL
    - Rate-limited: max 1 alert per minute per alert type
  - Setup Telegram bot: `@BotFather` → create bot → get token → store as `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

### 11.5 Post-Trade Analysis (TCA — Transaction Cost Analysis)

- **monitoring/tca.py**
  - `analyze_trade(trade_id) -> dict`
    - Implementation shortfall = (arrival price - fill price) * qty * side
    - Market impact estimate: compare price before/after your order
    - Opportunity cost: if limit order didn't fill, what was the cost?
  - Weekly TCA report: average slippage, fill rate, market impact, best/worst executions
  - Identify patterns: certain times of day have worse fills? Certain symbols more slippage?
  - Store TCA analysis in Supabase `tca_log`

### 11.6 Streamlit Dashboard (Lightweight Alternative)

- **monitoring/dashboard.py**
  - Quick-launch dashboard for non-Grafana setup
  - `streamlit run monitoring/dashboard.py`
  - Shows: equity curve, open positions, recent trades, agent verdicts, system status
  - Auto-refresh every 10 seconds using `st.experimental_rerun()`

### 11.7 Manual Verification Steps

- Start Prometheus + Grafana via Docker Compose; confirm metrics scraping
- Place a paper trade; confirm it appears on dashboard within 10s
- Trigger a 1.5% drawdown; confirm Telegram alert fires
- View TCA for last 10 trades; confirm slippage calculation is correct

---

## Phase 12: Deployment, Scheduling, and Cloud Infrastructure 🔴 NEW

**Goal:** Run 24/7 automatically. Market-hours-aware scheduling. Production cloud deployment.

### 12.1 Market Hours Scheduler

- **deployment/scheduler.py**
  - `is_market_open(asset_class: str) -> bool`
    - Equities: Mon–Fri 9:30am–4:00pm EST, excluding NYSE holidays
    - Crypto: always True
    - Forex: Sun 5pm–Fri 5pm EST (excluding major holidays)
  - `get_next_market_open(asset_class) -> datetime`
  - Market session tasks:

```python
    PRE_MARKET_TASKS = ["load_daily_state", "fetch_macro_events", "reset_drawdown_counter"]
    MARKET_OPEN_TASKS = ["start_ws_streams", "enable_trading", "run_consensus_loop"]
    MARKET_CLOSE_TASKS = ["generate_daily_report", "close_intraday_positions", "backup_to_supabase"]
    

```

- Use `APScheduler` (`pip install apscheduler`):

```python
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(pre_market_routine, "cron", hour=9, minute=15, timezone="America/New_York")
    scheduler.add_job(market_close_routine, "cron", hour=16, minute=5, timezone="America/New_York")
    

```

### 12.2 Docker Containerization

- **deployment/docker/Dockerfile**

```dockerfile
  FROM python:3.12-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install -r requirements.txt
  COPY . .
  ENV PYTHONUNBUFFERED=1
  CMD ["python", "-m", "scripts.run_live"]
  

```

- **deployment/docker/docker-compose.yml**

```yaml
  version: "3.9"
  services:
    dinetrade:
      build: .
      restart: unless-stopped
      env_file: .env
      depends_on: [redis, prometheus]
    redis:
      image: redis:7-alpine
      restart: always
    prometheus:
      image: prom/prometheus
    grafana:
      image: grafana/grafana
  

```

- `restart: unless-stopped` ensures bot restarts after crashes or server reboots

### 12.3 AWS Deployment (Primary)

- **deployment/infra/aws/**
  - **Recommended:** AWS EC2 `t3.medium` (2 vCPU, 4GB RAM) in `us-east-1` (low latency to NYSE)
  - EC2 setup steps:
    1. Launch Ubuntu 22.04 AMI
    2. Install Docker + Docker Compose
    3. Clone repo; copy `.env`
    4. `docker compose up -d`
    5. Set up AWS CloudWatch for server monitoring
  - **Alternatively:** AWS ECS Fargate (serverless containers) for auto-scaling
  - **Redis:** AWS ElastiCache (Redis) for production-grade in-memory store
  - **Supabase:** already cloud-hosted, no change needed
  - **Networking:** Security group: allow inbound 3000 (Grafana), 9090 (Prometheus) from your IP only; outbound 443 (all APIs)
  - **Cost estimate:** ~$35/month (EC2 t3.medium + ElastiCache t3.micro)

### 12.4 GCP Deployment (Alternative)

- **deployment/infra/gcp/**
  - **Recommended:** GCP Compute Engine `e2-medium` in `us-east4` (Virginia — close to NYSE)
  - Same Docker Compose setup as AWS
  - Or use GCP Cloud Run for containerized serverless deployment
  - **Cost estimate:** ~$25/month

### 12.5 Production run_live.py

- **scripts/run_live.py**
  - Master entry point for production:

```python
    async def main():
        await setup_logging()
        await validate_all_api_keys()           # Fail fast if any key missing
        await check_kill_switch()               # Abort if TRADING_ENABLED=false
        await stream_manager.start_all()        # WebSocket streams
        await scheduler.start()                 # Market hours scheduler
        await consensus_loop()                  # Main trading loop
    
    if __name__ == "__main__":
        asyncio.run(main())
    

```

- Health check endpoint: `http://localhost:8080/health` returns `{"status": "ok", "uptime_s": N}`

### 12.6 Secrets Management

- **NEVER commit `.env` to Git**
- Production secrets storage options:
  - AWS Secrets Manager (recommended for AWS)
  - GCP Secret Manager (recommended for GCP)
  - Docker secrets (for Docker Swarm)
  - HashiCorp Vault (self-hosted, max security)
- `config/settings.py` should fallback: try Secrets Manager first, then env var

### 12.7 Manual Verification Steps

- Build Docker image; confirm container starts and connects to all APIs
- Deploy to cloud VM; confirm bot runs through a full market session
- Simulate crash: `docker kill dinetrade`; confirm `restart: unless-stopped` brings it back within 10s
- Confirm Grafana dashboard accessible from your IP only (not public)
- Rotate one API key; confirm secrets management picks up new key without restart

---

## Phase 13: Latency Optimization 🟡 NEW (Advanced — Optional for V1 Live)

**Goal:** Reduce order submission latency from ~200ms to <20ms for time-sensitive strategies.

### 13.1 Python Optimization First (Do This Before C++/Rust)

- **Profile before optimizing:** `py-spy` or `cProfile` to find actual bottlenecks
- Common Python speedups:
  - `asyncio` already implemented — ensures non-blocking I/O
  - `numpy` vectorized operations for all technical indicators (no Python loops)
  - `ujson` or `orjson` instead of standard `json` for 3-5x faster serialization
  - `redis` pipeline batching: group multiple Redis commands into one round trip
  - LRU cache (`functools.lru_cache`) on expensive pure functions (e.g. ATR calculation)
  - Pre-compile Regex patterns at import time

### 13.2 Critical Path Analysis

- **The latency budget (target: <50ms end-to-end):**

```
  Market tick arrives via WebSocket        →  ~1ms
  Feature engineering (Python/numpy)       →  ~5ms
  Agent scoring (cached/simplified)        →  ~10ms
  Risk checks                              →  ~2ms
  Order construction + validation          →  ~2ms
  Order submission to broker API           →  ~20ms (network)
  ─────────────────────────────────────────────────
  Total target                             →  <40ms
  

```

- Gemini API call (~500ms) must be **async background task** — never in the critical path
- Pre-compute Gemini scores every N minutes; cache result; use cached score for order decisions

### 13.3 Cython for Hot Path Functions

- Compile Python functions to C for 10-50x speedup:

```python
  # indicators.pyx (Cython file)
  def compute_rsi(double[:] closes, int period=14):
      # Pure C implementation
      ...
  

```

- Compile: `python setup.py build_ext --inplace`
- Use only for: indicator computation, OBI calculation, price validation

### 13.4 Optional: Rust Extension (Advanced)

- Build a Rust module with `PyO3` for microsecond-level order serialization and WebSocket handling
- Scope: only if backtesting shows your alpha decays faster than 50ms (HFT territory)
- For most retail strategies (holding minutes to hours), Python is sufficient

### 13.5 Co-Location (Ultimate Latency)

- Move cloud VM to AWS `us-east-1` (same region as Alpaca's infrastructure)
- Use AWS Direct Connect for dedicated network path (expensive — only for HFT)
- For most strategies: co-location is unnecessary and not worth the cost

---

## Phase 14: Self-Evolution and Auto-Improvement 🟡 NEW

**Goal:** The bot learns from its own performance, mutates underperforming strategies, and improves over time.

### 14.1 Performance Tracker

- **evolution/performance_tracker.py**
  - Track every trade outcome with full context snapshot at time of decision:
    - Agent verdicts and reasoning
    - Market regime at time of trade
    - Macro environment (Fed rate, VIX level)
    - Technical signals (RSI, MACD, OBI)
    - News sentiment score
    - Actual outcome: PnL, hold duration, max favorable/adverse excursion
  - `compute_strategy_metrics(lookback_days=30) -> dict`
    - Win rate, avg winner, avg loser, Sharpe, max drawdown
    - By regime: performance breakdown in trending vs ranging markets
    - By asset class: equities vs crypto vs forex
    - By signal: which individual agent (Researcher/Sentiment/Chartist) has best predictive power?
  - Store in Supabase `strategy_performance` table

### 14.2 Agent Weight Optimization

- **evolution/strategy_mutator.py**
  - Currently: consensus requires ALL 3 agents to APPROVE
  - Optimize: weight agents by their recent IC (Information Coefficient)

```python
    # If Sentiment has IC=0.12 but Chartist has IC=0.02:
    AGENT_WEIGHTS = {
        "researcher": 0.40,
        "sentiment": 0.40,
        "chartist": 0.20,    # Reduced weight — not predictive recently
    }
    CONSENSUS_THRESHOLD = 0.7  # Weighted score threshold
    

```

- `rebalance_agent_weights(performance_data) -> dict`
  - Run monthly; compute each agent's IC over last 60 days
  - Update weights proportionally to IC
  - Apply min weight floor (10%) so no agent is completely ignored

### 14.3 Parameter Auto-Tuning

- **evolution/auto_retrain.py**
  - Periodically re-optimize key parameters using recent data:
    - ATR stop multiplier (currently 2.0)
    - Consensus threshold (currently score >= 7)
    - Kelly fraction (currently half-Kelly)
    - TWAP/VWAP duration
  - Method: **Bayesian Optimization** (`pip install optuna`)

```python
    import optuna
    def objective(trial):
        atr_mult = trial.suggest_float("atr_mult", 1.5, 3.5)
        threshold = trial.suggest_int("threshold", 6, 9)
        # Run walk-forward backtest with these params
        result = run_walk_forward(params={"atr_mult": atr_mult, "threshold": threshold})
        return result["sharpe"]
    
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=100)
    

```

- Run auto-tuning weekly on Sunday; update params only if improvement > 10% Sharpe
- Never auto-tune with live money — always test on out-of-sample data first

### 14.4 Universe Expansion Agent

- **evolution/universe_scanner.py**
  - Periodically scan for new alpha opportunities:
    - Screen S&P 500 for highest alpha factor IC
    - Screen crypto for new coins with strong momentum + volume
    - Screen forex pairs for regime changes
  - `score_universe_candidate(symbol) -> float`
    - Runs Researcher + Chartist on candidate
    - Checks liquidity (avg daily volume > $10M)
    - Checks correlation to existing universe (< 0.7 to existing positions)
  - Monthly universe review: add top 3 new candidates, remove bottom 3 performers
  - Candidates stored in Supabase `universe_candidates` with analysis

### 14.5 Feedback Loop — Vector DB Memory (Tie-In to Phase 10.5)

- After each trade closes:
  - Embed the decision context (agent reasoning + market state) with outcome (PnL)
  - `vector_db.upsert_memory(trade_id, reasoning_text, {pnl, regime, symbol})`
- Before each new trade:
  - Query for similar past situations
  - If historical analogues had -3 average PnL → downweight the signal
  - If historical analogues had +5 average PnL → upweight the signal
- This creates a self-improving system where past mistakes reduce future risk

### 14.6 Monthly Performance Review Automation

- **evolution/monthly_review.py**
  - Auto-generate monthly report:
    - Total PnL, Sharpe ratio, max drawdown
    - Best and worst trades (with full context)
    - Agent accuracy breakdown
    - Strategy param changes made
    - Universe changes made
  - Export as PDF to Supabase storage + send via Telegram
  - Compare to SPY/BTC benchmark (alpha = bot_return - benchmark_return)

---

## Complete Phase Summary


| Phase | Title                      | Status                       | Priority |
| ----- | -------------------------- | ---------------------------- | -------- |
| 0     | Environment Setup          | ✅ V1 (model names corrected) | Must Do  |
| 1     | Paper Skeleton (Equities)  | ✅ V1                         | Must Do  |
| 2     | Multi-Agent Foundation     | ✅ V1                         | Must Do  |
| 3     | Risk Executor + Recovery   | ✅ V1                         | Must Do  |
| 4     | Data Layer + Logging       | ✅ V1                         | Must Do  |
| 5     | Backtesting + RegimeTest   | ✅ V1                         | Must Do  |
| 6     | Hardening + Kill-Switch    | ✅ V1                         | Must Do  |
| 7     | Live Data Streaming 🔴     | NEW                          | Must Do  |
| 8     | Crypto + Forex 🔴          | NEW                          | Must Do  |
| 9     | Advanced Execution 🔴      | NEW                          | Must Do  |
| 10    | Intelligence Expansion 🔴  | NEW                          | High     |
| 11    | Monitoring + Dashboards 🔴 | NEW                          | High     |
| 12    | Deployment + Cloud 🔴      | NEW                          | Must Do  |
| 13    | Latency Optimization 🟡    | NEW                          | Medium   |
| 14    | Self-Evolution 🟡          | NEW                          | Medium   |


---

## Full Technology Stack


| Layer                | Technology                                                                       |
| -------------------- | -------------------------------------------------------------------------------- |
| Language             | Python 3.12 (primary), Cython (hot path), optional Rust                          |
| LLM                  | Gemini 3.1 Pro Preview (Researcher), Gemini 3 Flash Preview (Sentiment/Chartist) |
| Equities Broker      | Alpaca (paper → live)                                                            |
| Crypto Broker        | Binance (testnet → mainnet)                                                      |
| Forex Broker         | OANDA (practice → live)                                                          |
| Market Data (REST)   | Alpaca, FMP, OANDA, Binance                                                      |
| Market Data (Stream) | Alpaca WebSocket, Polygon.io WebSocket, Binance WebSocket                        |
| News (Live)          | Alpaca News WebSocket (free), FMP NewsAPI                                        |
| SEC Filings          | EDGAR RSS Watcher                                                                |
| Dark Pool            | Unusual Whales / Quiver Quant API                                                |
| Vector DB            | Pinecone (financial memory)                                                      |
| Cache / Streams      | Redis (local Docker or Upstash)                                                  |
| Persistent DB        | Supabase (PostgreSQL)                                                            |
| Metrics              | Prometheus + Grafana                                                             |
| Alerting             | Telegram Bot                                                                     |
| Scheduling           | APScheduler                                                                      |
| Backtesting          | Custom vectorized engine                                                         |
| Optimization         | Optuna (Bayesian)                                                                |
| Deployment           | Docker + AWS EC2 us-east-1                                                       |
| Audio                | OpenAI Whisper (earnings calls)                                                  |


---

## Complete Feature Checklist

### Strategy & Pre-Trade Planning

- Universe Selection (Equities, Forex, Crypto) — Phase 0/8
- Backtesting Engine (Vectorized) — Phase 5
- Walk-Forward Optimization — Phase 5
- Monte Carlo Simulations — Phase 5
- Alpha Factor Research — Phase 10.6
- Broker API (Alpaca, Binance, OANDA) — Phase 0/8
- Capital Allocation (Kelly Criterion) — Phase 2.5
- Account Margin / Leverage Scaling — Phase 2.4

### Intelligence & Market Analysis

- LLM Sentiment Extraction (Gemini 3.x) — Phase 2.2
- SEC Filing Analysis (8-K, 10-K, 10-Q) — Phase 10.2
- Earnings Call Sentiment (Audio + Text) — Phase 10.3
- Geopolitical Macro Tracking — Phase 10.4
- Cross-Asset Correlation Modeling — Phase 8.7
- Whale / Dark Pool Flow Monitoring — Phase 10.1
- Order Book Imbalance Detection — Phase 9.7
- Market Regime Classification — Phase 9.8

### System Engineering & Infrastructure

- High-Frequency Data Pipelines (WebSocket) — Phase 7
- Distributed Multi-Agent Architecture — Phase 2/3
- Vector Database (Pinecone) — Phase 10.5
- Real-Time Feature Engineering — Phase 7.4
- Latency Optimization (Cython/Rust) — Phase 13
- Failover & Redundancy — Phase 6/12
- Database Schema (Tick Logging) — Phase 4
- Cloud Infrastructure (AWS) — Phase 12.3

### Technical Mechanics & Patterns

- OHLCV Pattern Recognition — Phase 2.3
- Volume Profile (VWAP) — Phase 9.2
- RSI/MACD/Bollinger Convergence — Phase 2.3
- Mean Reversion Z-Score — Phase 9.8 (regime)
- Order Flow Trading (OBI) — Phase 9.7
- Liquidity / Fair Value Gaps — Phase 10.1 (dark pool)
- Institutional Footprint Analysis — Phase 10.1

### Risk Management & Defense

- Dynamic ATR Stop Loss — Phase 9.5
- Trailing Take-Profit — Phase 9.6
- Maximum Drawdown Circuit Breakers — Phase 3
- Position Sizing (Volatility Adjusted + Kelly) — Phase 2.5
- Correlated Asset Exposure Limits — Phase 8.7
- Black Swan Kill-Switch Protocols — Phase 6.1
- Slippage & Spread Monitoring — Phase 9.9
- Fat-Finger & API Error Handling — Phase 9.10

### Execution & Live Operations

- Smart Order Routing (SOR) — Phase 9.4
- TWAP Execution Algorithm — Phase 9.1
- VWAP Execution Algorithm — Phase 9.2
- Iceberg / Hidden Order Management — Phase 9.3
- Hedge Ratio Rebalancing — Phase 8.5
- Live Performance Dashboards (Grafana) — Phase 11.2
- Post-Trade Analysis (TCA) — Phase 11.5
- Real-Time PnL & Equity Curve — Phase 11.3

---

*DineTrade V2 — Total Phases: 14 | Total Feature Coverage: 100% of original spec*