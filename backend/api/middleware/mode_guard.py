# UI-1.3 Mode Guard Middleware — safety layer: block trade execution in Analysis mode at API level
import asyncio
import os

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

TRADE_ENDPOINTS = {"/api/trade/execute", "/api/trade/paper"}
LIVE_ENDPOINTS = {"/api/trade/live"}


async def mode_guard(request: Request, call_next):
    redis = getattr(request.app.state, "redis", None)
    if redis is not None:
        raw = await asyncio.to_thread(redis.get, "trading_mode")
        current_mode = (raw.decode() if isinstance(raw, bytes) else raw) or "analysis"
    else:
        current_mode = "analysis"

    if request.url.path in TRADE_ENDPOINTS and current_mode == "analysis":
        raise HTTPException(
            status_code=403,
            detail="Trade execution blocked in Analysis mode",
        )

    if request.url.path in LIVE_ENDPOINTS:
        live_enabled = os.getenv("LIVE_TRADING_ENABLED", "false").lower() == "true"
        if not live_enabled:
            raise HTTPException(
                status_code=403,
                detail="Live trading not enabled. Set LIVE_TRADING_ENABLED=true in config",
            )

    return await call_next(request)


class ModeGuardMiddleware(BaseHTTPMiddleware):
    """Runs mode_guard before each request."""

    async def dispatch(self, request: Request, call_next):
        return await mode_guard(request, call_next)
