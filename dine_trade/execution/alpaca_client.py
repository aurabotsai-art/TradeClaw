"""Alpaca client: get_latest_quote(symbol), smart_limit_order(symbol, side, qty, time_in_force_sec=60), get_account()."""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from typing import Any

import requests

from dine_trade.config.settings import (
    APCA_API_BASE_URL,
    APCA_API_KEY_ID,
    APCA_API_SECRET_KEY,
    UNIVERSE_DEFAULT,
)
from dine_trade.data.connectors.alpaca_connector import (
    get_latest_quote_mid,
    get_latest_price,
    get_ohlcv,
)

logger = logging.getLogger(__name__)

# Lazy REST client (requires alpaca-trade-api)
_rest: Any = None
_alpaca_failure_count = 0
_ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "").strip()

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover
    redis = None  # type: ignore[assignment]

_redis_client: "redis.Redis | None" = None  # type: ignore[name-defined]


def _get_rest():
    global _rest
    if _rest is not None:
        return _rest
    try:
        from alpaca_trade_api.rest import REST
        from alpaca_trade_api.common import URL
        base = (APCA_API_BASE_URL or "https://paper-api.alpaca.markets").rstrip("/")
        # REST builds URL as base_url + '/v2' + path; so base must not include /v2
        if base.endswith("/v2"):
            base = base[:-3].rstrip("/")
        _rest = REST(
            key_id=APCA_API_KEY_ID or "",
            secret_key=APCA_API_SECRET_KEY or "",
            base_url=URL(base),
        )
    except Exception as e:
        logger.exception("Failed to create Alpaca REST client: %s", e)
        raise
    return _rest


def _get_redis_client() -> "redis.Redis | None":  # type: ignore[name-defined]
    """Best-effort Redis client for idempotency keys."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if redis is None:
        return None
    try:
        url = os.getenv("REDIS_URL", "").strip() or "redis://localhost:6379/0"
        _redis_client = redis.Redis.from_url(url)
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to create Redis client for Alpaca idempotency: %s", e)
        _redis_client = None
    return _redis_client


def get_latest_quote(symbol: str) -> dict[str, float | None]:
    """Return dict with bid, ask, mid from Alpaca quote. For execution pricing."""
    bid, ask, mid = get_latest_quote_mid(symbol)
    return {"bid": bid, "ask": ask, "mid": mid}


def get_account() -> Any:
    """Get Alpaca account (paper or live)."""
    return _get_rest().get_account()


def validate_order(symbol: str, qty: float, price: float, side: str) -> tuple[bool, str]:
    """Audit fat-finger validation for Alpaca orders.

    - Price must be within 2% of last known market price.
    - Qty must not exceed 5% of 30-day average daily volume.
    - Symbol must be in approved universe list.
    """
    sym = (symbol or "").strip().upper()
    if sym not in [s.upper() for s in UNIVERSE_DEFAULT]:
        return False, f"Symbol {sym} not in approved universe."

    try:
        qty_f = float(qty)
        price_f = float(price)
    except (TypeError, ValueError):
        return False, "qty and price must be numeric."
    if qty_f <= 0 or price_f <= 0:
        return False, "qty and price must be positive."

    # Price vs last known market price (within 2%)
    mkt = get_latest_price(sym)
    if mkt is None or mkt <= 0:
        return False, f"Unable to fetch last market price for {sym}."
    deviation_pct = abs(price_f - mkt) / mkt * 100.0
    if deviation_pct > 2.0:
        return False, f"Limit price deviation {deviation_pct:.2f}% exceeds 2.00% tolerance."

    # Qty vs 30-day average daily volume (5% cap)
    try:
        df = get_ohlcv(sym, days=30)
    except Exception as e:  # pragma: no cover
        logger.warning("validate_order: get_ohlcv failed for %s: %s", sym, e)
        return False, "Unable to fetch historical volume for size check."
    if df.empty or "volume" not in df.columns:
        return False, "Volume data unavailable for size check."
    avg_vol = float(df["volume"].mean())
    if avg_vol <= 0:
        return False, "Average volume is non-positive; cannot size order safely."
    max_qty = avg_vol * 0.05
    if qty_f > max_qty:
        return False, f"Order qty {qty_f:.0f} exceeds 5%% of 30-day average volume ({max_qty:.0f})."

    return True, ""


def _validate_order_inputs(symbol: str, side: str, qty: float) -> tuple[bool, str | None, str, float]:
    """Basic sanity checks for symbol, side, and quantity."""
    sym = (symbol or "").strip().upper()
    if not sym:
        return False, "symbol must be non-empty", sym, qty
    if len(sym) > 10:
        return False, f"symbol '{sym}' too long", sym, qty

    side_norm = (side or "").lower()
    if side_norm not in {"buy", "sell"}:
        return False, f"side must be 'buy' or 'sell', got '{side}'", sym, qty

    try:
        qty_f = float(qty)
    except (TypeError, ValueError):
        return False, "qty must be a number", sym, 0.0
    if qty_f <= 0:
        return False, "qty must be positive", sym, qty_f

    return True, None, sym, qty_f


def smart_limit_order(
    symbol: str,
    side: str,
    qty: float,
    time_in_force_sec: int = 60,
) -> dict[str, Any]:
    """
    Submit limit order at current quote mid; cancel after time_in_force_sec if not filled.
    Returns dict with order response and status (e.g. filled, canceled).
    """
    ok, err, symbol_norm, qty_norm = _validate_order_inputs(symbol, side, qty)
    if not ok:
        return {"ok": False, "error": err, "order": None}

    bid, ask, mid = get_latest_quote_mid(symbol)
    if mid is None:
        return {"ok": False, "error": "No quote mid available", "order": None}

    limit_price = round(mid, 2)
    # Fat-finger validate against last known market price and volume.
    valid, v_err = validate_order(symbol_norm, qty_norm, limit_price, side)
    if not valid:
        logger.warning("Alpaca validate_order failed for %s: %s", symbol_norm, v_err)
        return {"ok": False, "error": v_err, "order": None}

    rest = _get_rest()
    order_id_holder: list[str | None] = [None]

    def cancel_after():
        oid = order_id_holder[0]
        if not oid:
            return
        time.sleep(time_in_force_sec)
        try:
            rest.cancel_order(oid)
            logger.info("Canceled order %s after %ss TIF", oid, time_in_force_sec)
        except Exception as e:
            logger.warning("Cancel order %s failed (may already be filled): %s", oid, e)

    # Submit with simple retry + backoff on transient Alpaca errors.
    max_retries = 3
    backoff_seconds = 2.0

    # Idempotency key stored in Redis with 60s TTL; reused across retries.
    idem_key = f"alpaca-{uuid.uuid4().hex}"
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            redis_client.setex(f"idempotency:{idem_key}", 60, "1")
        except Exception as e:  # pragma: no cover
            logger.warning("Failed to store Alpaca idempotency key in Redis: %s", e)

    try:
        from alpaca_trade_api.rest import APIError  # type: ignore
    except Exception:  # pragma: no cover - fallback if alpaca type unavailable
        APIError = Exception  # type: ignore[assignment]

    last_error: str | None = None

    for attempt in range(1, max_retries + 1):
        try:
            order = rest.submit_order(
                symbol=symbol_norm,
                qty=qty_norm,
                side=side.lower(),
                type="limit",
                time_in_force="day",
                limit_price=str(limit_price),
                client_order_id=idem_key,
            )
            order_id_holder[0] = getattr(order, "id", None) or (order if isinstance(order, dict) else {}).get("id")
            # Cancel after time_in_force_sec in background
            t = threading.Thread(target=cancel_after, daemon=True)
            t.start()

            out = order._raw if hasattr(order, "_raw") else (order if isinstance(order, dict) else {})
            global _alpaca_failure_count
            _alpaca_failure_count = 0
            return {"ok": True, "order": out, "limit_price": limit_price, "order_id": order_id_holder[0]}
        except APIError as e:  # type: ignore[misc]
            status = getattr(e, "status_code", None)
            msg = str(e)
            last_error = msg
            # HTTP 429 (rate limit): backoff and retry.
            if status == 429 and attempt < max_retries:
                logger.warning(
                    "Alpaca APIError on submit_order (status=%s, attempt=%s/%s): %s",
                    status,
                    attempt,
                    max_retries,
                    msg,
                )
                time.sleep(backoff_seconds)
                backoff_seconds *= 2
                continue

            # HTTP 500+ (server errors): do not retry blindly; log and alert.
            logger.error(
                "Alpaca server/APIError on submit_order (status=%s, attempt=%s/%s): %s",
                status,
                attempt,
                max_retries,
                msg,
            )
            break
        except Exception as e:
            last_error = str(e)
            logger.exception("smart_limit_order unexpected failure (attempt %s/%s): %s", attempt, max_retries, e)
            if attempt < max_retries:
                time.sleep(backoff_seconds)
                backoff_seconds *= 2
                continue
            break

    # If we reach here, all attempts failed.
    # Track consecutive failures and optionally send webhook alert.
    global _alpaca_failure_count
    _alpaca_failure_count += 1
    if _ALERT_WEBHOOK_URL and _alpaca_failure_count >= 3:
        try:
            payload = {
                "source": "alpaca_client.smart_limit_order",
                "message": f"Alpaca submit_order failed {__name__}, failure_count={_alpaca_failure_count}",
                "last_error": last_error,
            }
            requests.post(_ALERT_WEBHOOK_URL, json=payload, timeout=5)
        except Exception as e:  # pragma: no cover
            logger.warning("Failed to send Alpaca alert webhook: %s", e)

    return {"ok": False, "error": last_error or "Unknown Alpaca error", "order": None}
