---
name: TradeClaw UI — Full Build Plan V1.0
brand: aurabotsai-art
overview: >
  Complete plan to build TradeClaw — a pixel-perfect Claude.ai-style interface
  connected to the full DineTrade V2 backend (Phases 0–14). Exact Claude layout,
  dark theme, left icon sidebar, centered greeting, bottom input box, collapsible
  chat history — rebranded as TradeClaw with all 14 phases of trading intelligence
  wired in. Deployed live on AWS + accessible from any browser.
---

# TradeClaw: Full UI Build Plan V1.0
### Exact Claude Design · All 14 Bot Features · Live Deployed · aurabotsai-art

**Prerequisite:** DineTrade V2 backend Phases 0–6 complete (confirmed).
**Goal:** Build the frontend → wire it to the backend → deploy live → bot trades automatically while you chat with it.

---

## What This Plan Produces

When complete, you open `https://tradeclaw.yourdomain.com` in your browser and see:

```
┌─────────────────────────────────────────────────────────────────┐
│  [Icon]  [Icon]  [Icon]       Evening, Muhammad        [Avatar] │
│  [Icon]                                                         │
│  [Icon]     ┌─────────────────────────────────────┐            │
│  [Icon]     │  🦾 TradeClaw                        │            │
│  [Icon]     │                                      │            │
│  [Icon]     │  Evening, Muhammad                   │            │
│  [Icon]     │                                      │            │
│  [Icon]     │  [Analyze] [Trade] [PnL] [Backtest]  │            │
│  [Icon]     │                                      │            │
│  [Icon]     │  ┌────────────────────────────────┐  │            │
│  [Icon]     │  │ Type / for commands...         │  │            │
│  [Icon]     │  │                          [+][▶]│  │            │
│  [Icon]     │  └────────────────────────────────┘  │            │
│  [Icon]     │  [Analysis][Paper][Regime][Backtest]  │            │
│             └─────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

**Exact Claude.ai layout:** icon-only left sidebar, centered content, bottom-anchored input box, left chat history drawer, user avatar top-right — all rebranded TradeClaw with orange accent color.

---

## Technology Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Frontend framework | **React 18 + Vite** | Fast, component-based, easy WebSocket |
| Styling | **Tailwind CSS** | Utility-first, matches Claude's precision spacing |
| Real-time | **WebSocket (native)** + **EventSource (SSE)** | Streaming bot responses |
| Charts | **Recharts** + **lightweight-charts (TradingView)** | Equity curve + candlesticks |
| Backend framework | **FastAPI (Python)** | Already Python, async, WebSocket support |
| Auth | **Supabase Auth** | Already using Supabase |
| Deployment | **Vercel (frontend)** + **AWS EC2 (backend)** | Free frontend CDN, existing backend server |
| Domain + SSL | **Cloudflare** | Free SSL, DNS, DDoS protection |
| Process manager | **PM2** | Auto-restart bot on crash |

---

## Full Folder Structure

```text
tradeclaw/
  frontend/                          ← React app (deployed to Vercel)
    src/
      components/
        layout/
          Sidebar.jsx                ← Exact Claude icon sidebar
          ChatHistory.jsx            ← Collapsible history drawer
          TopBar.jsx                 ← Greeting + avatar (top right)
          InputBox.jsx               ← Bottom-anchored chat input
        chat/
          WelcomeScreen.jsx          ← Centered greeting + suggestion cards
          MessageList.jsx            ← Chat message feed
          MessageBubble.jsx          ← User + bot message styles
          ThinkingIndicator.jsx      ← Animated dots while agents run
          ToolCallBlock.jsx          ← Shows tool calls inline (Claude-style)
          AgentVerdictCards.jsx      ← 4-card agent consensus display
          TradeCard.jsx              ← Trade summary (entry/stop/target)
          StreamRenderer.jsx         ← SSE streaming response handler
        panels/
          ComputerPanel.jsx          ← Right side AI Computer panel
          StatusTab.jsx              ← System status + circuit breaker
          AgentsTab.jsx              ← Last agent run details
          ActionLogTab.jsx           ← Real-time tool call log
          RiskTab.jsx                ← Risk meters + Kelly sizing
          PositionsTab.jsx           ← Open + closed positions
        views/
          TradeView.jsx              ← /trade route — positions + orders
          MonitorView.jsx            ← /monitor route — equity curve + metrics
          BacktestView.jsx           ← /backtest route — RegimeTest results
          UniverseView.jsx           ← /universe route — symbol management
          RiskView.jsx               ← /risk route — all risk params
          HistoryView.jsx            ← /history route — past sessions
        modals/
          LiveModeConfirm.jsx        ← Double-confirm before live trading
          KillSwitchModal.jsx        ← Emergency stop UI
          SettingsModal.jsx          ← API keys, capital, risk params
          SymbolPickerModal.jsx      ← Add/remove universe symbols
      hooks/
        useWebSocket.js              ← WebSocket connection to backend
        useSSEStream.js              ← Streaming response handler
        useTradingState.js           ← Global bot state (mode, DD, positions)
        useLivePrices.js             ← Polling/WS price updates
      stores/
        chatStore.js                 ← Chat history (Zustand)
        tradingStore.js              ← Positions, PnL, drawdown (Zustand)
        settingsStore.js             ← User config, mode, model (Zustand)
      api/
        tradeclawApi.js              ← All fetch() calls to FastAPI backend
      utils/
        formatters.js                ← Price, date, PnL formatters
        intentParser.js              ← Detects user intent client-side
      App.jsx
      main.jsx
      index.css                      ← Tailwind + CSS variables (Claude palette)
    public/
      favicon.ico                    ← TradeClaw claw icon
    package.json
    tailwind.config.js
    vite.config.js

  backend/                           ← FastAPI server (on AWS EC2)
    api/
      main.py                        ← FastAPI app entry point
      routers/
        chat.py                      ← POST /chat, GET /chat/stream (SSE)
        trade.py                     ← POST /trade, GET /positions
        monitor.py                   ← GET /pnl, GET /equity-curve, GET /drawdown
        backtest.py                  ← POST /backtest/run, GET /backtest/results
        universe.py                  ← GET/POST/DELETE /universe
        risk.py                      ← GET /risk/state, POST /risk/kill-switch
        agents.py                    ← GET /agents/last-run
        news.py                      ← GET /news/:symbol
        auth.py                      ← POST /auth/verify (Supabase JWT)
      websocket/
        price_ws.py                  ← WS /ws/prices — live price stream
        log_ws.py                    ← WS /ws/logs — action log stream
        state_ws.py                  ← WS /ws/state — DD, CB, positions
      middleware/
        auth_middleware.py           ← JWT verification on every request
        mode_guard.py                ← Blocks trade endpoints in Analysis mode
        rate_limiter.py              ← Prevent accidental API floods
      orchestration/
        chat_orchestrator.py         ← Intent detection + tool routing
        stream_responder.py          ← SSE generator for streaming responses
        tool_registry.py             ← All tools with mode-based access control
      schemas/
        chat_schemas.py              ← Pydantic models for chat
        trade_schemas.py             ← Pydantic models for trades
        monitor_schemas.py           ← Pydantic models for metrics
    requirements_api.txt             ← FastAPI dependencies
    .env                             ← All secrets (never committed)

  deployment/
    nginx/
      tradeclaw.conf                 ← Nginx reverse proxy config
    pm2/
      ecosystem.config.js            ← PM2 process config for bot + API
    scripts/
      deploy.sh                      ← One-command deploy script
      setup_server.sh                ← Fresh EC2 setup script
    docker-compose.yml               ← All services together
    Dockerfile.backend               ← Backend container
```

---

## Phase UI-0: Design System and Exact Claude Layout

**Goal:** Build the pixel-perfect Claude.ai layout shell before any trading logic. Get the look exactly right first.

### UI-0.1 Color System and Typography

**CSS Variables (exact Claude dark theme palette + TradeClaw orange):**

```css
/* frontend/src/index.css */
:root {
  /* Backgrounds — exact Claude dark values */
  --bg-base:     #1a1a1a;   /* Main background */
  --bg-raised:   #222222;   /* Sidebar, panels */
  --bg-overlay:  #2a2a2a;   /* Cards, input */
  --bg-hover:    #333333;   /* Hover states */

  /* Borders */
  --border-subtle:  #333333;
  --border-default: #404040;

  /* Text */
  --text-primary:   #ececec;
  --text-secondary: #9b9b9b;
  --text-muted:     #666666;

  /* TradeClaw Brand — orange accent (replaces Claude's salmon) */
  --accent:         #ff6b35;
  --accent-hover:   #ff8c5a;
  --accent-glow:    rgba(255, 107, 53, 0.15);

  /* Semantic */
  --green:  #4ade80;
  --red:    #f87171;
  --yellow: #fbbf24;
  --blue:   #60a5fa;

  /* Typography */
  --font-sans: 'Inter', -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --font-display: 'Syne', sans-serif;  /* TradeClaw brand headings */
}
```

**Tailwind config additions:**
```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        'tc-bg': '#1a1a1a',
        'tc-raised': '#222222',
        'tc-overlay': '#2a2a2a',
        'tc-border': '#333333',
        'tc-accent': '#ff6b35',
        'tc-green': '#4ade80',
        'tc-red': '#f87171',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Syne', 'sans-serif'],
      }
    }
  }
}
```

### UI-0.2 Exact Claude Left Sidebar (Icon-Only)

**Reference:** The Claude screenshot shows a narrow (~48px) left bar with stacked icons only — no text labels. Top section has navigation icons. Bottom has avatar.

```jsx
// components/layout/Sidebar.jsx
// Exact measurements from Claude screenshot:
// Width: 48px fixed
// Icon size: 20px
// Icon padding: 12px vertical, centered horizontal
// Active state: slightly lighter background pill
// No text, no labels, no expand button

const NAV_ICONS = [
  { icon: <PlusIcon />,     action: () => newChat(),          tooltip: "New chat" },
  { icon: <SearchIcon />,   route: '/search',                  tooltip: "Search" },
  { icon: <BriefcaseIcon/>, route: '/trade',                   tooltip: "Trade" },
  { icon: <ChatIcon />,     route: '/chat',                    tooltip: "Chats" },
  { icon: <BookIcon />,     route: '/history',                 tooltip: "History" },
  { icon: <GridIcon />,     route: '/universe',                tooltip: "Universe" },
  { icon: <CodeIcon />,     route: '/monitor',                 tooltip: "Monitor" },
];

// Bottom of sidebar:
// { icon: <DownloadIcon />, action: exportSession }
// { icon: <AvatarMA />,     action: openSettings }
```

**Sidebar CSS rules:**
- `width: 48px` — fixed, never expands
- `border-right: 1px solid var(--border-subtle)`
- `background: var(--bg-raised)`
- Icons: `color: var(--text-secondary)` default, `color: var(--text-primary)` on hover/active
- Active route: `background: var(--bg-hover)` pill around icon, no color change
- Avatar at bottom: `width: 28px, height: 28px, border-radius: 50%` — initials "MA" in circle

### UI-0.3 Exact Claude Top Bar

**Reference:** Very minimal. Claude shows model name ("Sonnet 4.6") top-center with dropdown arrow. Stars icon top-right. User avatar top-right corner.

```jsx
// components/layout/TopBar.jsx
// Height: 52px
// Left: nothing (sidebar handles nav)
// Center: nothing on home screen (greeting is in content area)
//         OR current chat title when in a session
// Right: [Stars/upgrade icon] [Avatar]

// When in active chat session, center shows:
// [Model selector dropdown] — "gemini-1.5-pro ▾"
// [Mode pill] — "Paper" or "Analysis" or "Live 🔒"
// [Computer toggle button]
```

### UI-0.4 Exact Claude Welcome / Home Screen

**Reference screenshot analysis:**
- Background: solid `#1a1a1a` — no gradients
- "Free plan · Upgrade" pill — top center above greeting
- "✳ Evening, Muhammad" — large centered serif-ish heading, asterisk/snowflake icon in salmon/orange
- Input box: centered, ~640px wide, rounded corners, `bg: #2a2a2a`
- Inside input: "Type / for commands" placeholder
- Bottom of input: `[+]` button left, `[Sonnet 4.6 ▾]` model selector, `[audio bars icon]` right
- Below input: pill buttons — `[✏ Write]` `[🎓 Learn]` `[</> Code]` `[☕ Life stuff]` `[🔵 From Drive]`
- No cards, no grid — just the input and the pills below it

**TradeClaw version:**
```jsx
// components/chat/WelcomeScreen.jsx

<div className="flex flex-col items-center justify-center h-full gap-6">

  {/* Plan pill — top, same as Claude */}
  <div className="plan-pill">
    Paper Mode · <span className="text-tc-accent cursor-pointer">Go Live →</span>
  </div>

  {/* Greeting — exact Claude style */}
  <h1 className="welcome-heading">
    <span className="tc-asterisk">✳</span>
    {getGreeting()}, Muhammad
  </h1>

  {/* Input box — exact Claude dimensions and style */}
  <InputBox />

  {/* Quick action pills — replaces Claude's Write/Learn/Code */}
  <div className="quick-pills">
    <Pill icon="🔍">Analyze</Pill>
    <Pill icon="⚡">Trade</Pill>
    <Pill icon="📊">PnL</Pill>
    <Pill icon="🧪">Backtest</Pill>
    <Pill icon="🐋">Whales</Pill>
    <Pill icon="🌊">Regime</Pill>
  </div>

</div>
```

**Greeting logic:**
```js
function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Evening'; // matches Claude's "Evening, Muhammad"
}
```

### UI-0.5 Exact Claude Input Box

**Reference screenshot analysis:**
- Outer container: `border-radius: 16px`, `background: #2a2a2a`, `border: 1px solid #404040`
- Top area: textarea, `placeholder: "Type / for commands"`, monospace or sans-serif
- Bottom row: `[+]` icon left · center empty · `[Model name ▾]` + `[audio icon]` right
- No send button visible in Claude (Enter to send) — TradeClaw adds subtle `[▶]` button
- On focus: border color → slightly lighter, subtle glow

```jsx
// components/layout/InputBox.jsx

<div className={`input-container ${focused ? 'focused' : ''}`}>
  <textarea
    ref={textareaRef}
    placeholder="Type / for commands"
    value={input}
    onChange={handleChange}
    onKeyDown={handleKeyDown}  // Enter = send, Shift+Enter = newline
    rows={1}
    className="input-textarea"
    style={{ height: 'auto' }}  // auto-grow
  />
  <div className="input-bottom-row">
    <button className="input-icon-btn" onClick={openAttach}>
      <PlusIcon size={16} />
    </button>
    <div className="input-right-controls">
      <ModelDropdown />
      <button className="input-icon-btn send-btn" onClick={send}>
        <AudioBarsIcon />  {/* matches Claude's icon — changes to arrow on input */}
      </button>
    </div>
  </div>
</div>
```

### UI-0.6 Chat History Left Drawer

**Reference:** Claude shows a drawer that slides in from the left OVER the icon sidebar when you click the chat icon. Shows recent chat sessions grouped by date.

```jsx
// components/layout/ChatHistory.jsx
// This is a DRAWER, not a second sidebar
// Width: 260px, slides over sidebar
// Shows:
//   TODAY:
//     "Analyze NVDA setup for today"
//     "Run consensus on BTC/USD"
//   YESTERDAY:
//     "2022 regime backtest results"
//     "Show open positions PnL"
//   THIS WEEK:
//     "Paper trade MSFT 1% risk"
```

**Drawer behavior:**
- Triggered by clicking the chat/history icon in sidebar
- Overlays the main content with a semi-transparent backdrop
- Click outside or press Escape → closes
- Each history item: session title (first message truncated), timestamp, active indicator

### UI-0.7 Manual Verification

- Open in browser: verify exact proportions match Claude screenshot
- Confirm sidebar is exactly 48px wide, icon-only, no text
- Confirm greeting shows correct time-based text
- Confirm input box auto-grows with text
- Confirm history drawer opens/closes correctly
- Compare side-by-side with Claude screenshot — pixel-check spacing

---

## Phase UI-1: FastAPI Backend Foundation

**Goal:** Build the FastAPI server that wraps the existing DineTrade Python backend and exposes clean REST + WebSocket endpoints for the React frontend.

### UI-1.1 FastAPI App Setup

```python
# backend/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize bot state, connect Redis, start WS streams
    await initialize_trading_state()
    await start_price_streams()
    yield
    # Shutdown: clean close all WebSocket connections
    await cleanup_streams()

app = FastAPI(title="TradeClaw API", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware,
    allow_origins=["https://tradeclaw.yourdomain.com", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(chat.router,     prefix="/api/chat",     tags=["chat"])
app.include_router(trade.router,    prefix="/api/trade",    tags=["trade"])
app.include_router(monitor.router,  prefix="/api/monitor",  tags=["monitor"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(universe.router, prefix="/api/universe", tags=["universe"])
app.include_router(risk.router,     prefix="/api/risk",     tags=["risk"])
app.include_router(agents.router,   prefix="/api/agents",   tags=["agents"])
app.include_router(news.router,     prefix="/api/news",     tags=["news"])
app.include_router(auth.router,     prefix="/api/auth",     tags=["auth"])
```

### UI-1.2 Authentication Middleware

Every request must carry a valid Supabase JWT. The middleware validates it before any handler runs.

```python
# backend/api/middleware/auth_middleware.py
from fastapi import Request, HTTPException
from supabase import create_client

async def verify_jwt(request: Request, call_next):
    # Public routes: /api/auth/login, /docs, /health
    if request.url.path in PUBLIC_ROUTES:
        return await call_next(request)

    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(401, "Missing token")

    try:
        user = supabase.auth.get_user(token)
        request.state.user = user
    except:
        raise HTTPException(401, "Invalid token")

    return await call_next(request)
```

### UI-1.3 Mode Guard Middleware

This is the safety layer. Prevents trade execution in Analysis mode at the API level — not just UI level.

```python
# backend/api/middleware/mode_guard.py
TRADE_ENDPOINTS = ["/api/trade/execute", "/api/trade/paper"]
LIVE_ENDPOINTS  = ["/api/trade/live"]

async def mode_guard(request: Request, call_next):
    current_mode = await redis.get("trading_mode") or "analysis"

    if request.url.path in TRADE_ENDPOINTS and current_mode == "analysis":
        raise HTTPException(403, "Trade execution blocked in Analysis mode")

    if request.url.path in LIVE_ENDPOINTS:
        live_enabled = os.getenv("LIVE_TRADING_ENABLED", "false") == "true"
        if not live_enabled:
            raise HTTPException(403, "Live trading not enabled. Set LIVE_TRADING_ENABLED=true in config")

    return await call_next(request)
```

### UI-1.4 All API Endpoints Reference

```python
# ── CHAT ──────────────────────────────────────────────
POST   /api/chat                    → { message } → starts session, returns session_id
GET    /api/chat/stream/{session_id} → SSE stream of response tokens + tool calls
GET    /api/chat/history             → list of past sessions from Supabase
GET    /api/chat/session/{id}        → full session messages

# ── TRADE ─────────────────────────────────────────────
POST   /api/trade/paper             → { symbol, side, params } → executes paper trade
POST   /api/trade/live              → { symbol, side, params } → executes live trade (gated)
GET    /api/trade/positions         → all open positions from Alpaca
GET    /api/trade/orders            → recent orders
DELETE /api/trade/position/{symbol} → close a position

# ── MONITOR ───────────────────────────────────────────
GET    /api/monitor/pnl             → { today_pnl, realized, unrealized }
GET    /api/monitor/equity-curve    → array of { date, equity } for chart
GET    /api/monitor/drawdown        → { current_pct, limit_pct, cb_fired }
GET    /api/monitor/metrics         → { sharpe, win_rate, avg_win, avg_loss }
GET    /api/monitor/tca             → transaction cost analysis summary

# ── BACKTEST ──────────────────────────────────────────
POST   /api/backtest/run            → { regime, symbol, start, end } → runs async
GET    /api/backtest/status/{id}    → check if backtest complete
GET    /api/backtest/results/{id}   → { return, sharpe, max_dd, win_rate }
GET    /api/backtest/regimes        → list of saved RegimeTest results

# ── UNIVERSE ──────────────────────────────────────────
GET    /api/universe                → current symbol universe
POST   /api/universe                → { symbol, asset_class } → add symbol
DELETE /api/universe/{symbol}       → remove symbol
GET    /api/universe/{symbol}/snapshot → OHLCV + price + headlines + agent history

# ── RISK ──────────────────────────────────────────────
GET    /api/risk/state              → full risk state (DD, CB, positions, Kelly)
GET    /api/risk/correlation        → correlation matrix of open positions
POST   /api/risk/kill-switch        → { enabled: bool } → toggle kill switch
POST   /api/risk/set-params         → { max_dd, per_trade_risk, atr_mult }

# ── AGENTS ────────────────────────────────────────────
GET    /api/agents/last-run         → last consensus run results (all 4 agents)
GET    /api/agents/weights          → current agent IC weights
POST   /api/agents/run-consensus    → { symbol } → trigger consensus manually

# ── NEWS ──────────────────────────────────────────────
GET    /api/news/{symbol}           → latest headlines for symbol
GET    /api/news/whales/{symbol}    → dark pool prints
GET    /api/news/sec/{symbol}       → recent SEC filings

# ── AUTH ──────────────────────────────────────────────
POST   /api/auth/login              → { email, password } → Supabase session
POST   /api/auth/logout
GET    /api/auth/me                 → current user info

# ── WEBSOCKETS ────────────────────────────────────────
WS     /ws/prices                   → streams { symbol, price, change } every 3s
WS     /ws/logs                     → streams action log entries in real-time
WS     /ws/state                    → streams { mode, dd_pct, cb_fired, positions }
```

### UI-1.5 Manual Verification

- Run `uvicorn api.main:app --reload --port 8000`
- Open `http://localhost:8000/docs` — confirm all endpoints visible in Swagger UI
- Test `/api/monitor/pnl` with a valid JWT — confirm response
- Connect to `ws://localhost:8000/ws/prices` — confirm price ticks arriving

---

## Phase UI-2: Chat Orchestrator and SSE Streaming

**Goal:** The most important backend component. Routes user messages to the right DineTrade tools and streams the response back token-by-token like Claude does.

### UI-2.1 Chat Orchestrator

```python
# backend/api/orchestration/chat_orchestrator.py

TOOL_REGISTRY = {
    # ── READ TOOLS (available in all modes) ──────────────
    "fetch_symbol_snapshot":  fetch_symbol_snapshot,   # OHLCV + price + news
    "get_trade_history":      get_trade_history,        # Supabase trade_log
    "get_drawdown_state":     get_drawdown_state,       # equity, DD, CB flag
    "get_positions":          get_positions,            # open positions
    "run_consensus_analysis": run_consensus_analysis,   # agents, no execution
    "get_backtest_results":   get_backtest_results,     # saved backtest data
    "get_whale_prints":       get_whale_prints,         # dark pool feed
    "get_sec_filings":        get_sec_filings,          # EDGAR watcher
    "get_macro_events":       get_macro_events,         # FOMC, CPI calendar
    "classify_regime":        classify_regime,          # market regime
    "get_agent_weights":      get_agent_weights,        # IC scores
    "get_tca_summary":        get_tca_summary,          # slippage analysis

    # ── ACTION TOOLS (Paper mode only) ───────────────────
    "risk_first_trade":       risk_first_trade,         # full pipeline
    "close_position":         close_position,           # close open position
    "cancel_order":           cancel_order,             # cancel pending order

    # ── ADMIN TOOLS (explicit user action only) ───────────
    "toggle_kill_switch":     toggle_kill_switch,       # emergency stop
    "run_backtest":           run_backtest_async,       # trigger backtest
    "update_universe":        update_universe,          # add/remove symbols
}

async def handle_message(session_id: str, message: str, mode: str) -> AsyncGenerator:
    """
    Main orchestrator. Returns an async generator that yields SSE events.
    Each event is either:
      - { type: "token", content: "..." }         ← streaming text
      - { type: "tool_start", name: "...", args }  ← tool call started
      - { type: "tool_result", name: "...", data } ← tool call result
      - { type: "agent_result", agent: "...", ... } ← agent verdict
      - { type: "trade_result", ... }              ← trade execution result
      - { type: "done" }                           ← stream complete
    """

    # 1. Detect intent
    intent = detect_intent(message)

    # 2. Build Gemini prompt with conversation history + tool context
    history = await get_session_history(session_id)
    system_prompt = build_system_prompt(mode, intent)
    available_tools = get_tools_for_mode(mode)

    # 3. Stream Gemini response
    async for event in stream_gemini_with_tools(
        system_prompt, history, message, available_tools
    ):
        yield event

        # 4. If Gemini calls a tool, execute it and stream the result
        if event["type"] == "tool_call":
            tool_name = event["name"]
            tool_args = event["args"]

            yield {"type": "tool_start", "name": tool_name, "args": tool_args}

            result = await execute_tool(tool_name, tool_args, mode)

            yield {"type": "tool_result", "name": tool_name, "data": result}

    # 5. Save to Supabase chat_sessions
    await save_session_message(session_id, "user", message)
    await save_session_message(session_id, "assistant", assembled_response)

    yield {"type": "done"}
```

### UI-2.2 Intent Detection

```python
# backend/api/orchestration/chat_orchestrator.py

INTENT_PATTERNS = {
    "analysis":    ["analyze", "what", "explain", "tell me", "show", "how is"],
    "trade":       ["trade", "buy", "sell", "paper trade", "enter", "position"],
    "monitoring":  ["pnl", "portfolio", "drawdown", "positions", "equity", "performance"],
    "backtest":    ["backtest", "regime", "2022", "simulate", "historical"],
    "intelligence":["whale", "sec", "dark pool", "filing", "earnings", "insider"],
    "regime":      ["regime", "trending", "ranging", "market condition", "vix"],
    "risk":        ["risk", "stop loss", "kelly", "circuit breaker", "kill switch"],
    "universe":    ["add symbol", "remove", "universe", "track", "watchlist"],
}

def detect_intent(message: str) -> str:
    message_lower = message.lower()
    for intent, keywords in INTENT_PATTERNS.items():
        if any(k in message_lower for k in keywords):
            return intent
    return "general"
```

### UI-2.3 SSE Streaming Endpoint

```python
# backend/api/routers/chat.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json

router = APIRouter()

@router.post("")
async def create_chat_session(body: ChatRequest, request: Request):
    session_id = str(uuid4())
    # Store initial state in Redis
    await redis.set(f"session:{session_id}:mode", body.mode or "analysis")
    return {"session_id": session_id}

@router.get("/stream/{session_id}")
async def stream_chat(session_id: str, message: str, request: Request):
    mode = await redis.get(f"session:{session_id}:mode") or "analysis"

    async def event_generator():
        async for event in handle_message(session_id, message, mode):
            # SSE format: "data: {json}\n\n"
            yield f"data: {json.dumps(event)}\n\n"

            # Check if client disconnected
            if await request.is_disconnected():
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        }
    )
```

### UI-2.4 System Prompt for Chat Orchestrator

```python
# backend/api/orchestration/chat_orchestrator.py

def build_system_prompt(mode: str, intent: str) -> str:
    return f"""You are TradeClaw, an AI trading assistant built on the DineTrade V2 system.
You manage a multi-agent trading bot with: Researcher (gemini-1.5-pro), Sentiment (gemini-1.5-flash),
Chartist (gemini-1.5-flash), Risk Officer (rule-based), and Executor.

CURRENT MODE: {mode.upper()}
{"⚡ Paper trading is ENABLED. You can execute trades." if mode == "paper" else "🔍 Analysis only. No trade execution."}

CAPITAL: $10,000 | DAILY DD LIMIT: 1.5% | PER TRADE RISK: 1%
KILL SWITCH: {"OFF — trading active" if not kill_switch_active else "🔴 ON — ALL TRADING HALTED"}

RULES:
- Always run DataValidator before any trade (two price sources within 0.1%)
- Always run Risk Officer check before any trade execution
- Never suggest bypassing circuit breakers or risk limits
- Always show agent verdicts transparently
- When a trade is rejected, clearly explain why (which agent vetoed, which limit was hit)
- Use tool calls to fetch real data — never make up prices or PnL figures
- Stream your reasoning naturally, like a conversation

When showing tool calls, format them clearly so the user understands what the system is doing.
After every trade, summarize: symbol, side, qty, entry, stop, target, R:R ratio, Kelly size.
"""
```

### UI-2.5 Manual Verification

- Send "Analyze NVDA" via POST → confirm SSE stream returns token events
- Confirm `tool_start` event fires before `tool_result`
- Send "Paper trade NVDA" in Analysis mode → confirm 403 from mode guard
- Switch to Paper mode → send same → confirm trade executes
- Disconnect client mid-stream → confirm generator cleans up

---

## Phase UI-3: React Frontend — Core Chat Interface

**Goal:** Build the React frontend with exact Claude layout. Pixel-perfect. Fully wired to the FastAPI SSE stream.

### UI-3.1 Project Setup

```bash
# In tradeclaw/frontend/
npm create vite@latest . -- --template react
npm install tailwindcss @tailwindcss/vite
npm install zustand                    # State management
npm install react-router-dom           # Routing for /trade, /monitor, etc.
npm install lucide-react               # Icons (same as Claude uses)
npm install recharts                   # Equity curve, PnL charts
npm install lightweight-charts        # TradingView-style candlestick chart
npm install @supabase/supabase-js      # Auth
npm install react-hot-toast            # Alerts (trade executed, CB fired)
npm install framer-motion              # Animations (panel open/close, message fade)
npm install eventsource-parser         # SSE parsing
```



```jsx
// src/App.jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';

export def### UI-3.2 App Router Structureault function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />           {/* 48px icon sidebar — always visible */}
        <ChatHistory />       {/* 260px drawer — opens on icon click */}
        <main className="main-content">
          <TopBar />
          <Routes>
            <Route path="/"          element={<ChatView />} />
            <Route path="/trade"     element={<TradeView />} />
            <Route path="/monitor"   element={<MonitorView />} />
            <Route path="/backtest"  element={<BacktestView />} />
            <Route path="/universe"  element={<UniverseView />} />
            <Route path="/risk"      element={<RiskView />} />
            <Route path="/history"   element={<HistoryView />} />
          </Routes>
        </main>
        <ComputerPanel />     {/* Right panel — toggleable */}
      </div>
    </BrowserRouter>
  );
}
```

### UI-3.3 SSE Streaming Hook

```js
// src/hooks/useSSEStream.js

export function useSSEStream() {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const send = async (sessionId, userMessage) => {
    setIsStreaming(true);

    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

    // Start bot message as empty
    const botMsgId = Date.now();
    setMessages(prev => [...prev, { role: 'bot', id: botMsgId, content: '', toolCalls: [] }]);

    // Connect SSE
    const url = `/api/chat/stream/${sessionId}?message=${encodeURIComponent(userMessage)}`;
    const eventSource = new EventSource(url);

    eventSource.onmessage = (e) => {
      const event = JSON.parse(e.data);

      if (event.type === 'token') {
        // Append token to last bot message
        setMessages(prev => prev.map(msg =>
          msg.id === botMsgId
            ? { ...msg, content: msg.content + event.content }
            : msg
        ));
      }

      if (event.type === 'tool_start') {
        // Add tool call block to message
        setMessages(prev => prev.map(msg =>
          msg.id === botMsgId
            ? { ...msg, toolCalls: [...msg.toolCalls, { name: event.name, args: event.args, status: 'running' }] }
            : msg
        ));
        // Also push to Computer panel log
        actionLogStore.add(event);
      }

      if (event.type === 'tool_result') {
        // Update tool call block status to done
        setMessages(prev => prev.map(msg =>
          msg.id === botMsgId
            ? { ...msg, toolCalls: msg.toolCalls.map(tc =>
                tc.name === event.name ? { ...tc, status: 'done', result: event.data } : tc
              )}
            : msg
        ));
        actionLogStore.update(event);
      }

      if (event.type === 'agent_result') {
        agentStore.update(event); // Update Computer panel Agents tab
      }

      if (event.type === 'trade_result') {
        tradingStore.addTrade(event.data);
        toast.success(`Trade executed: ${event.data.side} ${event.data.qty} ${event.data.symbol}`);
      }

      if (event.type === 'done') {
        setIsStreaming(false);
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      setIsStreaming(false);
      eventSource.close();
    };
  };

  return { messages, isStreaming, send };
}
```

### UI-3.4 Message Bubble Components

```jsx
// src/components/chat/MessageBubble.jsx
// Exact Claude style: no bubble background for bot, rounded bubble for user

function UserBubble({ content }) {
  return (
    <div className="flex justify-end mb-6">
      <div className="max-w-[70%] bg-tc-overlay border border-tc-border
                      rounded-2xl rounded-tr-md px-4 py-3 text-sm text-tc-text">
        {content}
      </div>
    </div>
  );
}

function BotMessage({ content, toolCalls, isStreaming }) {
  return (
    <div className="flex gap-4 mb-6 max-w-[760px]">
      {/* Bot avatar — TradeClaw claw icon, small */}
      <div className="bot-avatar">🦾</div>

      <div className="flex-1 flex flex-col gap-3">
        {/* Tool call blocks appear ABOVE the text response, like Claude */}
        {toolCalls.map(tc => <ToolCallBlock key={tc.name} toolCall={tc} />)}

        {/* Agent verdict cards if this was a consensus run */}
        {hasAgentResults(content) && <AgentVerdictCards />}

        {/* Main text response — markdown rendered */}
        <div className="prose prose-invert text-sm leading-relaxed">
          <MarkdownRenderer content={content} />
          {isStreaming && <BlinkingCursor />}
        </div>

        {/* Trade card if a trade was executed */}
        {hasTradeResult(content) && <TradeResultCard />}

        {/* Message meta */}
        <div className="text-xs text-tc-muted font-mono">
          {timestamp} · TradeClaw · {model}
        </div>
      </div>
    </div>
  );
}
```

### UI-3.5 Tool Call Blocks (Claude-style)

```jsx
// src/components/chat/ToolCallBlock.jsx
// Claude shows tool calls as expandable blocks ABOVE the response text
// TradeClaw shows them the same way

function ToolCallBlock({ toolCall }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="tool-block border border-tc-border rounded-xl overflow-hidden text-xs font-mono">
      <button
        className="tool-header w-full flex items-center gap-2 px-3 py-2
                   bg-tc-overlay text-tc-secondary hover:bg-tc-hover"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Icon based on tool name */}
        <ToolIcon name={toolCall.name} />
        <span className="text-tc-text">{formatToolName(toolCall.name)}</span>
        <span className="text-tc-muted ml-1">({formatArgs(toolCall.args)})</span>

        {/* Status badge */}
        <span className={`ml-auto status-badge ${toolCall.status}`}>
          {toolCall.status === 'running' ? '⟳ running' : '✓ done'}
        </span>

        <ChevronIcon rotated={expanded} />
      </button>

      {expanded && (
        <div className="tool-body px-3 py-2 text-tc-secondary">
          {JSON.stringify(toolCall.result, null, 2)}
        </div>
      )}
    </div>
  );
}

// Tool name → human label map
const TOOL_LABELS = {
  fetch_symbol_snapshot:  "Fetching market data",
  run_consensus_analysis: "Running agent consensus",
  risk_first_trade:       "Executing risk-first trade",
  get_drawdown_state:     "Checking drawdown state",
  get_whale_prints:       "Scanning dark pool prints",
  get_sec_filings:        "Reading SEC filings",
  classify_regime:        "Classifying market regime",
  run_backtest:           "Running backtest engine",
  // etc.
};
```

### UI-3.6 Agent Verdict Cards

```jsx
// src/components/chat/AgentVerdictCards.jsx
// Shows after a consensus run — 4 cards in a grid

function AgentVerdictCards({ results }) {
  return (
    <div className="grid grid-cols-2 gap-2 my-2">
      {results.map(agent => (
        <div key={agent.name}
          className={`agent-card p-3 rounded-xl border text-xs
            ${agent.verdict === 'APPROVE'
              ? 'border-green-500/30 bg-green-500/5'
              : 'border-red-500/30 bg-red-500/5'}`}
        >
          <div className="font-mono text-tc-muted uppercase tracking-wide text-[10px]">
            {agent.name} · {agent.model}
          </div>
          <div className={`font-display font-bold text-sm mt-1
            ${agent.verdict === 'APPROVE' ? 'text-tc-green' : 'text-tc-red'}`}>
            {agent.verdict} {agent.score && `· ${agent.score}/10`}
          </div>
          <div className="text-tc-secondary mt-1 leading-relaxed">
            {agent.reasoning}
          </div>
        </div>
      ))}
    </div>
  );
}
```

### UI-3.7 Trade Result Card

```jsx
// src/components/chat/TradeCard.jsx

function TradeCard({ trade }) {
  const pnl_color = trade.unrealized_pnl >= 0 ? 'text-tc-green' : 'text-tc-red';

  return (
    <div className="trade-card border border-tc-border rounded-2xl p-4 my-2">
      <div className="flex items-center justify-between mb-3">
        <span className="font-display font-black text-xl">{trade.symbol}</span>
        <span className={`px-2 py-1 rounded-lg text-xs font-mono
          ${trade.side === 'BUY' ? 'bg-green-500/10 text-tc-green' : 'bg-red-500/10 text-tc-red'}`}>
          {trade.side}
        </span>
      </div>
      <div className="grid grid-cols-4 gap-3 text-xs">
        <Stat label="Qty"    value={trade.qty} />
        <Stat label="Entry"  value={`$${trade.entry_price}`} />
        <Stat label="Stop"   value={`$${trade.stop_price}`}   color="text-tc-red" />
        <Stat label="Target" value={`$${trade.target_price}`} color="text-tc-green" />
        <Stat label="Risk"   value={`$${trade.risk_amount} (1%)`} />
        <Stat label="R:R"    value={`${trade.rr_ratio}x`} />
        <Stat label="Kelly"  value={`$${trade.kelly_size}`} />
        <Stat label="Algo"   value={trade.algo} />
      </div>
    </div>
  );
}
```

### UI-3.8 Manual Verification

- Send "Analyze NVDA" → confirm tokens stream in real-time with cursor blink
- Confirm tool call blocks appear collapsed above response text
- Click tool block → confirm it expands showing result JSON
- Run consensus → confirm 4-card agent grid appears
- Execute paper trade → confirm trade card appears + toast notification
- Test on mobile: confirm layout doesn't break below 768px

---

## Phase UI-4: Computer Panel (Right Side)

**Goal:** The AI Computer panel — a right-side collapsible panel showing live bot state, agent results, action log, risk meters, and positions.

### UI-4.1 Panel Architecture

```jsx
// src/components/panels/ComputerPanel.jsx

const PANEL_TABS = ['Status', 'Agents', 'Log', 'Risk', 'Positions', 'News'];

function ComputerPanel() {
  const { panelOpen } = useSettingsStore();
  const [activeTab, setActiveTab] = useState('Status');

  return (
    <AnimatePresence>
      {panelOpen && (
        <motion.div
          className="computer-panel w-[340px] border-l border-tc-border
                     bg-tc-raised flex flex-col h-full"
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 340, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        >
          <PanelHeader />
          <PanelTabs tabs={PANEL_TABS} active={activeTab} onSelect={setActiveTab} />
          <div className="panel-body flex-1 overflow-y-auto p-3">
            {activeTab === 'Status'    && <StatusTab />}
            {activeTab === 'Agents'    && <AgentsTab />}
            {activeTab === 'Log'       && <ActionLogTab />}
            {activeTab === 'Risk'      && <RiskTab />}
            {activeTab === 'Positions' && <PositionsTab />}
            {activeTab === 'News'      && <NewsTab />}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
```

### UI-4.2 Status Tab — Live via WebSocket

```jsx
// src/components/panels/StatusTab.jsx
// Pulls from WS /ws/state — updates every 3s

function StatusTab() {
  const state = useWebSocketState('/ws/state');
  const prices = useWebSocketState('/ws/prices');

  return (
    <div className="flex flex-col gap-3">

      {/* System status */}
      <Section title="System Status">
        <StatRow label="MODE"           value={state.mode.toUpperCase()} color="accent" />
        <StatRow label="TRADING_ENABLED" value={state.trading_enabled ? 'true' : 'false'} />
        <StatRow label="KILL_SWITCH"     value={state.kill_switch ? '🔴 ON' : 'OFF'} />
        <StatRow label="UPTIME"          value={state.uptime} />
        <StatRow label="WS_STREAMS"      value={`${state.streams_ok}/3 OK`} color="green" />
      </Section>

      {/* Circuit breaker — prominent */}
      <CircuitBreakerBadge
        fired={state.cb_fired}
        current_pct={state.dd_pct}
        limit_pct={1.5}
      />

      {/* Active symbol price */}
      <Section title="Active Symbol">
        <PriceDisplay
          symbol={state.active_symbol}
          price={prices[state.active_symbol]?.price}
          change={prices[state.active_symbol]?.change_pct}
        />
        <MiniSparkline data={prices[state.active_symbol]?.history} />
      </Section>

      {/* Latest news */}
      <Section title="Live News">
        <NewsFeed symbol={state.active_symbol} limit={3} />
      </Section>

    </div>
  );
}
```

### UI-4.3 Action Log Tab — Live via WebSocket

```jsx
// src/components/panels/ActionLogTab.jsx
// Pulls from WS /ws/logs — new entries pushed in real-time

function ActionLogTab() {
  const logs = useWebSocketState('/ws/logs');

  return (
    <div className="action-log flex flex-col gap-1">
      {logs.map(entry => (
        <LogEntry key={entry.id} entry={entry} />
      ))}
    </div>
  );
}

// Log entry format:
// { time, icon, text, status: 'ok'|'warn'|'error', expandable_data }
// Example entries:
// 14:32 ✅  smart_limit_order NVDA BUY — FILLED @ $891.20
// 14:31 🛡️  risk_officer → APPROVE max_qty=25
// 14:31 🤖  consensus → APPROVED 3/3 score=7.85
// 14:31 ✅  data_validator delta=0.019% OK
// 14:30 📊  fetch_ohlcv NVDA 100d → OK
// 14:30 📰  fetch_headlines NVDA → 12 items
```

### UI-4.4 Risk Tab

```jsx
// src/components/panels/RiskTab.jsx

function RiskTab() {
  const risk = useQuery('/api/risk/state');

  return (
    <div className="flex flex-col gap-3">
      <Section title="Risk Meters">
        <RiskBar label="Daily Drawdown"      current={risk.dd_pct}    max={1.5}  />
        <RiskBar label="Capital Deployed"    current={risk.deployed_pct} max={60} />
        <RiskBar label="Correlation Exposure" current={risk.corr_max}  max={0.85} />
        <RiskBar label="Avg Slippage (bps)"  current={risk.slippage}  max={5}    />
      </Section>
      <Section title="Kelly Sizing Today">
        <StatRow label="EQUITY"    value={`$${risk.equity}`} />
        <StatRow label="1% RISK ="  value={`$${risk.risk_per_trade}`} />
        <StatRow label="WIN_RATE"  value={`${risk.win_rate}%`} />
        <StatRow label="AVG_WIN"   value={`$${risk.avg_win}`} color="green" />
        <StatRow label="AVG_LOSS"  value={`$${risk.avg_loss}`} color="red" />
        <StatRow label="KELLY_F"   value={`${risk.kelly_f} (½ Kelly)`} color="accent" />
      </Section>
      <KillSwitchToggle enabled={risk.kill_switch} />
    </div>
  );
}
```

### UI-4.5 Manual Verification

- Open Computer panel → confirm animation is smooth
- Confirm Status tab updates in real-time without page refresh
- Confirm Action Log shows new entries when a consensus runs
- Trigger a paper trade → confirm log shows all 5 steps in sequence
- Trigger circuit breaker → confirm CB badge turns red immediately

---

## Phase UI-5: All Navigation Views

**Goal:** Build all 6 views accessible from the left sidebar. Each is a full-page replacement for the chat area.

### UI-5.1 Trade View (/trade)

```jsx
// src/components/views/TradeView.jsx
// Shows: open positions table, recent orders, daily PnL summary

Sections:
  1. Metric cards row: Today PnL | Open Positions | Daily DD | Capital Deployed
  2. Open Positions table:
     Symbol | Side | Qty | Entry | Current | Unrealized PnL | Stop | Actions
     [Close position] button on each row → opens confirm modal
  3. Recent Orders table (last 20):
     Time | Symbol | Side | Qty | Price | Fill Status | Algo | PnL
  4. "Paper trade" quick input at bottom of page
```

### UI-5.2 Monitor View (/monitor)

```jsx
// src/components/views/MonitorView.jsx

Sections:
  1. KPI cards: Equity | Sharpe (30d) | Max Drawdown | Win Rate | Avg Winner | Avg Loser
  2. Equity Curve chart (Recharts LineChart):
     - 30-day equity curve
     - Drawdown overlay (red shaded areas)
     - CB events marked with red dots
  3. Daily PnL bar chart (Recharts BarChart):
     - Green bars = profitable days
     - Red bars = losing days
     - Horizontal line at 0
  4. Agent Performance table:
     Agent | Model | IC (30d) | Weight | Accuracy | Total Trades
  5. Slippage Analysis (TCA):
     Avg slippage | Best execution | Worst execution | Fill rate
```

### UI-5.3 Backtest View (/backtest)

```jsx
// src/components/views/BacktestView.jsx

Sections:
  1. "Run Backtest" form:
     - Regime picker: [2022 Tech Bear] [Aug 2024 Spike] [2020 COVID] [Custom]
     - Symbol(s) picker
     - Date range
     - [Run] button → triggers POST /api/backtest/run → shows loading
  2. RegimeTest Results table (mandatory results always shown):
     Regime | Period | Return | Max DD | Sharpe | Circuit Breakers | Status
  3. Walk-Forward Results:
     Table of train/test windows with out-of-sample metrics
  4. Monte Carlo:
     - Distribution histogram of max drawdown across 1000 paths
     - Failure rate % (paths exceeding 1.5% daily DD)
  5. Last backtest equity curve (same chart as Monitor view)
```

### UI-5.4 Universe View (/universe)

```jsx
// src/components/views/UniverseView.jsx

Sections:
  1. Universe table:
     Symbol | Asset Class | Price | 24h Change | Avg Volume | IC Score | Status
     [Remove] button on each row
  2. [+ Add Symbol] button → opens SymbolPickerModal
  3. Universe scanner results (from Phase 14 auto-scanner):
     Candidates table: Symbol | Score | Why Recommended | [Add] button
  4. Correlation matrix heatmap:
     Color-coded grid of pairwise correlations for all universe symbols
```

### UI-5.5 Risk View (/risk)

```jsx
// src/components/views/RiskView.jsx

Sections:
  1. Risk parameter cards:
     Daily DD Limit | Per Trade Risk | Kelly Fraction | ATR Multiplier
  2. Risk parameters table with [Edit] buttons:
     Parameter | Value | Current | Status
  3. Kill Switch panel:
     Current state (ON/OFF) | Big red/green button | Last toggled time
  4. Post-mortem log (from Supabase post_mortem table):
     Date | Triggered At | Drawdown | Capital At Open | Positions Snapshot
  5. Circuit breaker history:
     Last 10 CB events with timestamps and recovery details
```

### UI-5.6 History View (/history)

```jsx
// src/components/views/HistoryView.jsx

Sections:
  1. Search bar: filter sessions by keyword
  2. Sessions grouped by date (TODAY, YESTERDAY, THIS WEEK, OLDER)
  3. Each session card:
     - First message (truncated)
     - Timestamp
     - Mode at time (Analysis / Paper / Live)
     - PnL from that session (if any trades happened)
     - [Open] button → loads session in chat view
  4. Export button: download full session history as JSON
```

### UI-5.7 Manual Verification

- Navigate to each view → confirm data loads from API
- Trade View: confirm close position button opens modal
- Monitor View: confirm equity curve renders from Supabase data
- Backtest View: run a backtest → confirm loading state → results appear
- Universe View: add a symbol → confirm appears in table → run bot → confirm it trades it
- Risk View: toggle kill switch → confirm bot stops trading immediately

---

## Phase UI-6: Modals and Safety Flows

**Goal:** All safety-critical user interactions happen through proper confirmation modals.

### UI-6.1 Live Mode Confirmation Modal

```jsx
// src/components/modals/LiveModeConfirm.jsx
// Triggered when user clicks "Live" mode tab

Step 1 — Warning screen:
  🔴 You are about to enable LIVE trading
  Real money will be at risk.
  Daily loss limit: $150 (1.5% of $10,000)
  [Cancel] [I understand, continue →]

Step 2 — Type to confirm:
  Type "I ACCEPT REAL MONEY RISK" to proceed:
  [text input]
  [Cancel] [Enable Live Trading]

Step 3 — Final state:
  Sets APCA_API_BASE_URL to live endpoint in backend
  Posts to /api/risk/set-live-mode
  Shows "Live mode active" confirmation toast
```

### UI-6.2 Kill Switch Modal

```jsx
// src/components/modals/KillSwitchModal.jsx
// Two states:

// State A: Kill switch is OFF (trading active)
<div>
  ⚡ Trading is currently ACTIVE
  Clicking below will immediately halt all trading.
  No new orders will be placed. Open positions will NOT be closed.
  [Cancel] [🔴 Activate Kill Switch]
</div>

// State B: Kill switch is ON (trading halted)
<div>
  🔴 Kill switch is ACTIVE — all trading halted
  [Close positions] button (optional)
  [Cancel] [✅ Resume Trading]
</div>
```

### UI-6.3 Settings Modal

```jsx
// src/components/modals/SettingsModal.jsx

Tabs:
  1. Capital & Risk:
     - Starting capital input
     - Daily DD limit (%)
     - Per trade risk (%)
     - ATR multiplier
     - Kelly fraction
  2. API Keys (masked, show/hide toggle):
     - GEMINI_API_KEY
     - APCA_API_KEY_ID / SECRET
     - BINANCE_API_KEY / SECRET
     - POLYGON_API_KEY
     - FMP_API_KEY
  3. Notifications:
     - Telegram bot token + chat ID
     - Alert thresholds (DD %, trade executed, CB fired)
  4. Appearance:
     - Accent color picker (default: TradeClaw orange)
     - Font size
     - Compact mode toggle
```

### UI-6.4 Manual Verification

- Click Live mode → confirm 3-step modal appears
- Type wrong confirmation string → confirm button stays disabled
- Activate kill switch → confirm bot stops → resume → confirm bot restarts
- Change capital in Settings → confirm Risk calculations update

---

## Phase UI-7: WebSocket Live Data Layer

**Goal:** The entire UI updates in real-time without page refreshes. Prices tick live. Logs stream. Positions update.

### UI-7.1 WebSocket Connections

```python
# backend/api/websocket/price_ws.py

@app.websocket("/ws/prices")
async def prices_websocket(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            # Get latest prices from Redis (populated by Alpaca WS connector)
            prices = {}
            for symbol in UNIVERSE:
                price_data = await redis.hgetall(f"price:{symbol}")
                prices[symbol] = {
                    "price": float(price_data.get("price", 0)),
                    "change_pct": float(price_data.get("change_pct", 0)),
                    "bid": float(price_data.get("bid", 0)),
                    "ask": float(price_data.get("ask", 0)),
                }
            await ws.send_json(prices)
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass
```

```python
# backend/api/websocket/log_ws.py

@app.websocket("/ws/logs")
async def logs_websocket(ws: WebSocket):
    await ws.accept()
    # Subscribe to Redis pub/sub channel "action_logs"
    pubsub = redis.pubsub()
    await pubsub.subscribe("action_logs")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await ws.send_text(message["data"])
    except WebSocketDisconnect:
        await pubsub.unsubscribe("action_logs")
```

```python
# backend/api/websocket/state_ws.py

@app.websocket("/ws/state")
async def state_websocket(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            state = {
                "mode":            await redis.get("trading_mode") or "analysis",
                "trading_enabled": await redis.get("trading_enabled") == "true",
                "kill_switch":     await redis.get("kill_switch") == "true",
                "cb_fired":        await redis.get("circuit_breaker_fired") == "true",
                "dd_pct":          float(await redis.get("daily_dd_pct") or 0),
                "active_symbol":   await redis.get("active_symbol") or "NVDA",
                "uptime":          get_uptime_str(),
                "streams_ok":      await count_healthy_streams(),
            }
            await ws.send_json(state)
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass
```

### UI-7.2 React WebSocket Hook

```js
// src/hooks/useWebSocket.js

export function useWebSocketState(endpoint) {
  const [data, setData] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    const url = `${WS_BASE_URL}${endpoint}`;
    wsRef.current = new WebSocket(url);

    wsRef.current.onmessage = (e) => {
      try { setData(JSON.parse(e.data)); } catch {}
    };

    wsRef.current.onclose = () => {
      // Reconnect after 2s
      setTimeout(() => wsRef.current = new WebSocket(url), 2000);
    };

    return () => wsRef.current?.close();
  }, [endpoint]);

  return data;
}
```

### UI-7.3 Manual Verification

- Open app → confirm prices updating every 3s without interaction
- Open Action Log tab → send a chat → confirm log entries appear immediately
- Kill network → wait 2s → restore → confirm WebSocket reconnects automatically
- Trigger circuit breaker → confirm CB badge in Computer panel turns red within 3s

---

## Phase UI-8: Authentication and Login Screen

**Goal:** Secure the app so only you can access it.

### UI-8.1 Login Screen

```jsx
// src/components/auth/LoginScreen.jsx
// Simple, Claude-style login

<div className="login-screen flex items-center justify-center h-screen bg-tc-bg">
  <div className="login-card w-[380px] bg-tc-raised border border-tc-border rounded-2xl p-8">

    {/* Logo */}
    <div className="flex items-center gap-3 mb-8">
      <div className="logo-icon">🦾</div>
      <div>
        <div className="font-display font-black text-xl">TradeClaw</div>
        <div className="text-xs text-tc-muted font-mono">aurabotsai-art</div>
      </div>
    </div>

    {/* Email + Password */}
    <Input label="Email" type="email" />
    <Input label="Password" type="password" />
    <Button variant="primary" className="w-full mt-4">Sign in</Button>

    {/* Google OAuth option */}
    <Button variant="outline" className="w-full mt-3">
      Continue with Google
    </Button>

  </div>
</div>
```

### UI-8.2 Protected Routes

```jsx
// src/App.jsx

function ProtectedRoute({ children }) {
  const { user } = useAuthStore();
  if (!user) return <Navigate to="/login" />;
  return children;
}

// All routes except /login wrapped in ProtectedRoute
```

### UI-8.3 JWT Handling

```js
// src/api/tradeclawApi.js
// Auto-attach JWT to every request

const api = {
  get: async (path) => {
    const token = supabase.auth.getSession()?.access_token;
    return fetch(`${API_BASE}${path}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    }).then(r => r.json());
  },
  // post, delete similar
};
```

---

## Phase UI-9: Deployment — Frontend + Backend + Bot

**Goal:** Everything live, accessible from browser, bot trading automatically.

### UI-9.1 Backend Deployment on EC2

```bash
# deployment/scripts/setup_server.sh
# Run once on fresh EC2 (Ubuntu 22.04, t3.medium, us-east-1)

# 1. System setup
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.12 python3-pip nodejs npm nginx certbot

# 2. Install PM2 (process manager)
sudo npm install -g pm2

# 3. Clone repo
git clone https://github.com/yourusername/tradeclaw.git
cd tradeclaw

# 4. Python deps
cd backend
pip install -r requirements.txt
pip install -r requirements_api.txt

# 5. Environment
cp .env.example .env
nano .env  # Fill in all API keys

# 6. Start all processes with PM2
pm2 start deployment/pm2/ecosystem.config.js
pm2 save  # Save so PM2 restarts on reboot
pm2 startup  # Auto-start PM2 on server boot
```

**PM2 ecosystem config:**
```js
// deployment/pm2/ecosystem.config.js
module.exports = {
  apps: [
    {
      name: "tradeclaw-api",
      script: "uvicorn",
      args: "api.main:app --host 0.0.0.0 --port 8000 --workers 2",
      cwd: "/home/ubuntu/tradeclaw/backend",
      env: { PYTHONPATH: "/home/ubuntu/tradeclaw" },
      restart_delay: 3000,
      max_restarts: 10,
    },
    {
      name: "tradeclaw-bot",
      script: "python",
      args: "scripts/run_live.py",
      cwd: "/home/ubuntu/tradeclaw",
      restart_delay: 5000,
      max_restarts: 5,
    },
    {
      name: "tradeclaw-streams",
      script: "python",
      args: "-m dine_trade.data.stream_manager",
      cwd: "/home/ubuntu/tradeclaw",
      restart_delay: 3000,
      max_restarts: 10,
    }
  ]
};
```

### UI-9.2 Nginx Reverse Proxy

```nginx
# deployment/nginx/tradeclaw.conf

server {
    listen 443 ssl;
    server_name api.tradeclaw.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/api.tradeclaw.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.tradeclaw.yourdomain.com/privkey.pem;

    # REST API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket endpoints — CRITICAL: must disable buffering
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;  # Keep WS alive for 24h
    }

    # SSE streaming — must disable buffering
    location /api/chat/stream/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header X-Accel-Buffering no;
        proxy_read_timeout 300;
    }
}
```

### UI-9.3 Frontend Deployment on Vercel

```bash
# In tradeclaw/frontend/
npm run build

# vercel.json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }  # SPA routing
  ],
  "env": {
    "VITE_API_BASE_URL": "https://api.tradeclaw.yourdomain.com",
    "VITE_WS_BASE_URL":  "wss://api.tradeclaw.yourdomain.com",
    "VITE_SUPABASE_URL": "https://xxx.supabase.co",
    "VITE_SUPABASE_ANON_KEY": "your-anon-key"
  }
}
```

```bash
# Deploy frontend to Vercel (free):
npx vercel --prod
# Custom domain: tradeclaw.yourdomain.com → point to Vercel
```

### UI-9.4 SSL Certificates

```bash
# On EC2 — get free SSL via Let's Encrypt
sudo certbot --nginx -d api.tradeclaw.yourdomain.com
# Auto-renews every 90 days
```

### UI-9.5 Domain Setup (Cloudflare)

```
DNS Records:
  tradeclaw.yourdomain.com        → CNAME → vercel.app    (frontend)
  api.tradeclaw.yourdomain.com    → A     → EC2 public IP (backend)

Cloudflare settings:
  SSL/TLS mode: Full (strict)
  WebSockets: ON (required for WS connections)
  Cache level: Bypass for /api/* paths
```

### UI-9.6 Go-Live Checklist

```
BEFORE GOING LIVE (Paper):
□ All API keys set in production .env
□ PAPER_MODE=true confirmed
□ PM2 shows all 3 processes running (tradeclaw-api, tradeclaw-bot, tradeclaw-streams)
□ Nginx serving HTTPS on both domains
□ Frontend loads at https://tradeclaw.yourdomain.com
□ Login works with Supabase credentials
□ Chat sends a message → response streams correctly
□ Computer panel WebSockets connecting (no console errors)
□ Paper trade executes end-to-end: chat → consensus → executor → Alpaca paper
□ Telegram alert fires on test trade
□ Kill switch test: activate → bot stops → deactivate → bot resumes

BEFORE GOING LIVE (Real Money):
□ 2 weeks of paper trading with consistent positive results
□ Run full RegimeTest suite — all pass
□ Change ALPACA_BASE_URL to live endpoint
□ Set LIVE_TRADING_ENABLED=true in .env
□ Start with $2,000 (20% of capital) for first week
□ Monitor Grafana dashboard daily
□ Have kill switch bookmarked on phone
```

### UI-9.7 Manual Verification (Full E2E)

1. Open `https://tradeclaw.yourdomain.com` on your phone
2. Log in
3. Type: "Analyze NVDA and run a paper trade if consensus approves"
4. Watch tokens stream in real-time
5. See tool call blocks appear: `fetch_ohlcv` → `run_consensus` → `risk_first_trade`
6. See agent verdict cards render
7. See trade card appear with entry/stop/target
8. Open Computer panel → Log tab → confirm all steps logged
9. Open Alpaca paper account → confirm order placed
10. Wait for fill → Telegram message arrives: "Trade executed"

---

## Phase UI-10: Polish, Performance, Mobile

**Goal:** Make it feel like a real product, not a dev tool.

### UI-10.1 Loading States

Every async operation has a loading state:
- Chat streaming: animated thinking indicator (3 dots, Claude-style)
- Trade executing: "Routing through risk pipeline…" status text + spinner
- Backtest running: progress bar with "Processed X/1247 bars"
- Data loading on views: skeleton screens (not spinners)

### UI-10.2 Error Handling

```jsx
// Global error boundary
// API error → toast notification with error message
// WebSocket disconnect → "Reconnecting…" banner at top
// Circuit breaker fires → full-screen alert banner (dismissible)
// Kill switch activated remotely → "⚠️ Kill switch active" persistent banner
```

### UI-10.3 Mobile Responsive

```css
/* Mobile: sidebar becomes bottom tab bar */
@media (max-width: 768px) {
  .sidebar { 
    position: fixed; bottom: 0; left: 0; right: 0;
    width: 100%; height: 56px;
    flex-direction: row;
    border-top: 1px solid var(--border-subtle);
    border-right: none;
  }
  .computer-panel { display: none; } /* Panel hidden on mobile */
  .chat-history-drawer { width: 100%; } /* Full-width drawer */
}
```

### UI-10.4 Keyboard Shortcuts

```
Enter       → Send message
Shift+Enter → New line in input
Cmd/Ctrl+K  → Focus input from anywhere
Cmd/Ctrl+B  → Toggle Computer panel
Cmd/Ctrl+H  → Open chat history
Cmd/Ctrl+,  → Open Settings
Escape      → Close any open modal/drawer
```

---

## Complete Phase Summary

| Phase | Title | Builds | Output |
|-------|-------|--------|--------|
| UI-0 | Design System | CSS vars, fonts, colors, exact Claude layout shell | Pixel-perfect empty shell |
| UI-1 | FastAPI Backend | All 20+ endpoints, auth, mode guard, WebSocket servers | Working API server |
| UI-2 | Chat Orchestrator | SSE streaming, intent detection, tool routing | Streaming chat backend |
| UI-3 | React Chat UI | Message bubbles, tool blocks, agent cards, trade cards | Working chat interface |
| UI-4 | Computer Panel | All 6 tabs, live WebSocket data, real-time log | Live bot status panel |
| UI-5 | Navigation Views | Trade, Monitor, Backtest, Universe, Risk, History | All 6 full-page views |
| UI-6 | Modals & Safety | Live mode confirm, kill switch, settings | Safe production flows |
| UI-7 | WebSocket Layer | Price ticking, log streaming, state syncing | Real-time everything |
| UI-8 | Auth | Supabase login, JWT middleware, protected routes | Secure access |
| UI-9 | Deployment | EC2 + PM2 + Nginx + Vercel + Cloudflare + SSL | Live at your domain |
| UI-10 | Polish | Loading states, error handling, mobile, shortcuts | Production quality |

---

## What You Type in Cursor to Build This

### Session 1 (UI-0): Layout Shell
> "Build the React + Tailwind app shell for TradeClaw. Create the exact Claude.ai layout: 48px icon-only left sidebar (icons: new chat, search, briefcase, chat bubbles, book, grid, code), centered main content area, bottom-anchored input box with auto-grow textarea. Use the CSS variables in UI-0.1. No trading logic yet — just the layout skeleton."

### Session 2 (UI-0 continued): Welcome Screen
> "Build the WelcomeScreen component. Exact Claude.ai style: centered layout, 'Evening, Muhammad' greeting with ✳ icon in #ff6b35 orange, greeting changes based on time of day. Input box below. Below the input: 6 pill buttons: Analyze, Trade, PnL, Backtest, Whales, Regime. Reference the Claude screenshot for exact proportions."

### Session 3 (UI-1): FastAPI Foundation
> "Build the FastAPI backend in backend/api/main.py. Include all routers from the endpoint list in Phase UI-1.4. Add CORS middleware, JWT auth middleware (Supabase), and mode guard middleware. Add lifespan handler. Use Python 3.12, FastAPI, pydantic v2."

### Session 4 (UI-2): Chat Orchestrator + SSE
> "Build the chat orchestrator in backend/api/orchestration/chat_orchestrator.py. It must: detect intent from user message, build system prompt including current mode and capital, call Gemini 1.5 Pro with tool calling, yield SSE events for tokens/tool_calls/agent_results/trade_results. Implement the /api/chat and /api/chat/stream/{id} endpoints with proper SSE headers."

### Session 5 (UI-3): React Chat Components
> "Build MessageBubble, ToolCallBlock, AgentVerdictCards, and TradeCard components. ToolCallBlock must be collapsible like Claude's tool calls. AgentVerdictCards shows 4 cards in a 2x2 grid. TradeCard shows entry/stop/target/Kelly in a clean grid. All dark theme using tc-* Tailwind classes."

### Session 6 (UI-4): Computer Panel
> "Build the ComputerPanel component with 6 tabs: Status, Agents, Log, Risk, Positions, News. Status tab pulls from WS /ws/state. Log tab pulls from WS /ws/logs. Panel slides in from the right with framer-motion animation. 340px wide."

### Session 7 (UI-7+UI-1): WebSocket Backend
> "Build the three WebSocket endpoints: /ws/prices (reads from Redis, sends every 3s), /ws/logs (subscribes to Redis pub/sub channel 'action_logs', pushes in real-time), /ws/state (reads all state keys from Redis, sends every 3s). Add reconnection logic on the React side."

### Session 8 (UI-9): Deployment
> "Write the deployment config: PM2 ecosystem.config.js for 3 processes (tradeclaw-api, tradeclaw-bot, tradeclaw-streams), Nginx config with WebSocket and SSE support, Vercel vercel.json with SPA routing, and setup_server.sh for EC2 Ubuntu 22.04."

---

## After All Phases Complete — Final State

```
You open https://tradeclaw.yourdomain.com

You see: ✳ Evening, Muhammad

You type: "Analyze NVDA — paper trade if consensus approves"

You watch:
  → fetch_ohlcv(NVDA, 100d) ✓
  → fetch_headlines(NVDA) → 12 items ✓
  → run_consensus(NVDA) → asyncio.gather…
      Researcher: APPROVE 8.4 ✓
      Sentiment:  APPROVE 7.9 ✓
      Chartist:   APPROVE 7.2 ✓
      Risk Officer: APPROVE max_qty=25 ✓
  → data_validator delta=0.019% ✓
  → smart_limit_order NVDA BUY 25 @$891.20 60s ✓
  → trade_log INSERT ✓

Bot response streams in naturally.
Trade card appears: NVDA BUY · Entry $891.20 · Stop $878.40 · Target $917.00
Telegram: "✅ Trade executed: BUY 25 NVDA"
Computer panel Log tab: all 8 steps visible in real-time.

Meanwhile, the bot is running on EC2.
It scanned 5 symbols this morning.
It found 2 setups. Executed both.
It's managing stops automatically.
You didn't touch anything.
```

**That is the complete output of this plan.**

---

*TradeClaw UI V1.0 — aurabotsai-art · Built on DineTrade V2 backend (Phases 0–14)*
