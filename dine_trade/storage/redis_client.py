"""Redis: equity_at_open, circuit_breaker, last_trade_time. Optional.

This module provides a very thin wrapper around redis-py for storing a few
pieces of *daily* state with a 24h TTL:

- equity_at_open
- circuit_breaker flag (whether it has fired today)
- last_trade_time

If Redis is not configured or available, all functions degrade gracefully:
- setters become no-ops
- getters return None / False
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    import redis
except ImportError:  # pragma: no cover - redis is optional dependency
    redis = None  # type: ignore


_redis_client: Optional["redis.Redis"] = None
_TTL_SECONDS = 24 * 60 * 60  # 24 hours


def _get_client() -> "redis.Redis":
    """Return a Redis client or raise RuntimeError if not configured/installed."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    if redis is None:
        raise RuntimeError("redis package is not installed.")

    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        # Fallback to localhost default if REDIS_URL is not set
        url = "redis://localhost:6379/0"

    _redis_client = redis.Redis.from_url(url)
    return _redis_client


# ---------------------------------------------------------------------------
# equity_at_open
# ---------------------------------------------------------------------------

def set_equity_at_open(equity: float) -> None:
    """Store today's equity_at_open with a 24h TTL."""
    try:
        client = _get_client()
    except RuntimeError:
        return

    key = _key("equity_at_open")
    client.set(key, float(equity), ex=_TTL_SECONDS)


def get_equity_at_open() -> Optional[float]:
    """Return today's equity_at_open or None if not set/available."""
    try:
        client = _get_client()
    except RuntimeError:
        return None

    key = _key("equity_at_open")
    val = client.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# circuit_breaker flag
# ---------------------------------------------------------------------------

def set_circuit_breaker_triggered(triggered: bool) -> None:
    """Store today's circuit_breaker flag with a 24h TTL."""
    try:
        client = _get_client()
    except RuntimeError:
        return

    key = _key("circuit_breaker")
    client.set(key, "1" if triggered else "0", ex=_TTL_SECONDS)


def get_circuit_breaker_triggered() -> bool:
    """Return True if today's circuit_breaker flag is set, else False."""
    try:
        client = _get_client()
    except RuntimeError:
        return False

    key = _key("circuit_breaker")
    val = client.get(key)
    return val == b"1"


# ---------------------------------------------------------------------------
# last_trade_time
# ---------------------------------------------------------------------------

def set_last_trade_time(ts: Optional[datetime] = None) -> None:
    """Store the ISO timestamp of the last trade with a 24h TTL."""
    try:
        client = _get_client()
    except RuntimeError:
        return

    if ts is None:
        ts = datetime.now(timezone.utc)
    key = _key("last_trade_time")
    client.set(key, ts.isoformat(), ex=_TTL_SECONDS)


def get_last_trade_time() -> Optional[datetime]:
    """Return last_trade_time as a datetime or None if not set/available."""
    try:
        client = _get_client()
    except RuntimeError:
        return None

    key = _key("last_trade_time")
    val = client.get(key)
    if val is None:
        return None
    try:
        # val is bytes; decode then parse
        s = val.decode("utf-8")
        return datetime.fromisoformat(s)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _key(suffix: str) -> str:
    """Build a namespaced Redis key for today's date and given suffix."""
    today = datetime.now(timezone.utc).date().isoformat()
    return f"dinetra de:{today}:{suffix}".replace(" ", "")

