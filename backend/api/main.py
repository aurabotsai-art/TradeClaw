# UI-1.1 FastAPI App Setup — TradeClaw API
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.auth_middleware import AuthMiddleware
from api.middleware.mode_guard import ModeGuardMiddleware
from api.routers import (
    agents,
    auth,
    backtest,
    chat,
    monitor,
    news,
    risk,
    trade,
    universe,
)


async def initialize_trading_state():
    """Startup: initialize bot state, connect Redis. Stub until wired to dine_trade."""
    pass


async def start_price_streams():
    """Startup: start WS streams. Stub until wired to stream_manager."""
    pass


async def cleanup_streams():
    """Shutdown: clean close all WebSocket connections."""
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize bot state, connect Redis, start WS streams
    await initialize_trading_state()
    await start_price_streams()
    yield
    # Shutdown: clean close all WebSocket connections
    await cleanup_streams()


app = FastAPI(title="TradeClaw API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tradeclaw.yourdomain.com", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)
app.add_middleware(ModeGuardMiddleware)

# Mount all routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(trade.router, prefix="/api/trade", tags=["trade"])
app.include_router(monitor.router, prefix="/api/monitor", tags=["monitor"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(universe.router, prefix="/api/universe", tags=["universe"])
app.include_router(risk.router, prefix="/api/risk", tags=["risk"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "TradeClaw API"}


# ── WEBSOCKETS ────────────────────────────────────────
# Stub: wire to stream_manager for real { symbol, price, change } every 3s
@app.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket):
    """Stream latest prices from Redis for the current universe."""
    from dine_trade.config.settings import UNIVERSE_DEFAULT
    from dine_trade.storage.redis_client import _get_client as _get_redis_client  # type: ignore[attr-defined]

    await websocket.accept()
    try:
        redis = _get_redis_client()
    except Exception:
        # If Redis not available, keep connection open but send empty payloads.
        redis = None

    try:
        while True:
            prices = {}
            for symbol in UNIVERSE_DEFAULT:
                if redis is None:
                    prices[symbol] = {
                        "price": 0.0,
                        "change_pct": 0.0,
                        "bid": 0.0,
                        "ask": 0.0,
                    }
                    continue
                key = f"price:{symbol}"
                try:
                    data = redis.hgetall(key)
                except Exception:
                    data = {}
                # redis-py returns dict[bytes, bytes]; decode keys
                decoded = {k.decode("utf-8"): v.decode("utf-8") for k, v in data.items()} if data else {}
                prices[symbol] = {
                    "price": float(decoded.get("price", "0") or 0),
                    "change_pct": float(decoded.get("change_pct", "0") or 0),
                    "bid": float(decoded.get("bid", "0") or 0),
                    "ask": float(decoded.get("ask", "0") or 0),
                }
            await websocket.send_json(prices)
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# Stub: wire to action log for real-time entries
@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    """Stream action logs from Redis pub/sub channel 'action_logs'."""
    from dine_trade.storage.redis_client import _get_client as _get_redis_client  # type: ignore[attr-defined]

    await websocket.accept()
    try:
        redis = _get_redis_client()
    except Exception:
        # No Redis; just keep connection idle.
        redis = None

    if redis is None:
        try:
            while True:
                await asyncio.sleep(5)
        except WebSocketDisconnect:
            return

    pubsub = redis.pubsub()
    await pubsub.subscribe("action_logs")
    try:
        async for message in pubsub.listen():
            if message.get("type") == "message":
                data = message.get("data")
                # data may be bytes
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="ignore")
                await websocket.send_text(str(data))
    except WebSocketDisconnect:
        await pubsub.unsubscribe("action_logs")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# Stub: wire to Redis/state for { mode, dd_pct, cb_fired, positions }
@app.websocket("/ws/state")
async def ws_state(websocket: WebSocket):
    """Stream high-level trading state from Redis."""
    from dine_trade.storage.redis_client import _get_client as _get_redis_client  # type: ignore[attr-defined]

    await websocket.accept()
    try:
        redis = _get_redis_client()
    except Exception:
        redis = None

    def _get_bool(val: bytes | None) -> bool:
        if val is None:
            return False
        try:
            s = val.decode("utf-8").lower()
        except Exception:
            return False
        return s in ("1", "true", "yes")

    def _get_str(val: bytes | None, default: str) -> str:
        if val is None:
            return default
        try:
            return val.decode("utf-8")
        except Exception:
            return default

    def _get_float(val: bytes | None) -> float:
        if val is None:
            return 0.0
        try:
            return float(val.decode("utf-8"))
        except Exception:
            return 0.0

    async def _get_uptime_str() -> str:
        # For now, rely on API process uptime based on a simple timestamp in Redis (optional).
        if redis is None:
          return "unknown"
        try:
            started = redis.get("api_start_time")
            if not started:
                return "unknown"
            import datetime
            started_f = float(started.decode("utf-8"))
            delta = datetime.datetime.now().timestamp() - started_f
            mins = int(delta // 60)
            hrs = mins // 60
            return f\"{hrs}h {mins % 60}m\"
        except Exception:
            return "unknown"

    async def _count_healthy_streams() -> int:
        if redis is None:
            return 0
        count = 0
        try:
            for key in ("stream:alpaca", "stream:news", "stream:polygon"):
                val = redis.get(key)
                if _get_bool(val):
                    count += 1
        except Exception:
            return 0
        return count

    try:
        while True:
            if redis is None:
                state = {
                    "mode": "analysis",
                    "trading_enabled": False,
                    "kill_switch": False,
                    "cb_fired": False,
                    "dd_pct": 0.0,
                    "active_symbol": "NVDA",
                    "uptime": "unknown",
                    "streams_ok": 0,
                }
            else:
                mode = _get_str(redis.get("trading_mode"), "analysis")
                trading_enabled = _get_bool(redis.get("trading_enabled"))
                kill_switch = _get_bool(redis.get("kill_switch"))
                cb_fired = _get_bool(redis.get("circuit_breaker_fired"))
                dd_pct = _get_float(redis.get("daily_dd_pct"))
                active_symbol = _get_str(redis.get("active_symbol"), "NVDA")
                uptime = await _get_uptime_str()
                streams_ok = await _count_healthy_streams()

                state = {
                    "mode": mode,
                    "trading_enabled": trading_enabled,
                    "kill_switch": kill_switch,
                    "cb_fired": cb_fired,
                    "dd_pct": dd_pct,
                    "active_symbol": active_symbol,
                    "uptime": uptime,
                    "streams_ok": streams_ok,
                }
            await websocket.send_json(state)
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

