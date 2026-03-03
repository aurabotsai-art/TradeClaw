"""Central alerting system for DineTrade.

Alert channels:
  - Telegram bot (preferred, minimal friction)
  - Slack webhook (optional)
  - Email (hook point only; requires external SMTP setup)

Usage:

    from dine_trade.monitoring.alerting import send_alert

    send_alert("WARNING", "Daily drawdown exceeded 1.0%", {"drawdown_pct": 1.2})

Alert levels:
  - INFO
  - WARNING
  - CRITICAL

Rate limiting:
  - Max 1 alert per minute per alert *type* (alert_type argument).
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "").strip()

# Simple in-process rate limiter: alert_type -> last_sent_unix
_last_sent_per_type: Dict[str, float] = {}
_RATE_LIMIT_SECONDS = 60.0


def _rate_limited(alert_type: str) -> bool:
    now = time.time()
    last = _last_sent_per_type.get(alert_type)
    if last is not None and (now - last) < _RATE_LIMIT_SECONDS:
        return True
    _last_sent_per_type[alert_type] = now
    return False


def _format_alert_message(level: str, message: str, data: Optional[Dict[str, Any]]) -> str:
    parts = [f"[{level.upper()}] {message}"]
    if data:
        try:
            parts.append(json.dumps(data, separators=(",", ":"), default=str))
        except Exception:
            # Fallback to repr if JSON fails
            parts.append(repr(data))
    return "\n".join(parts)


def _send_telegram(msg: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
        resp = requests.post(url, json=payload, timeout=10)
        if not resp.ok:
            logger.warning("Telegram alert failed: %s %s", resp.status_code, resp.text[:200])
    except Exception:
        logger.debug("Telegram alert exception", exc_info=True)


def _send_slack(msg: str) -> None:
    if not SLACK_WEBHOOK_URL:
        return
    try:
        payload = {"text": msg}
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        if not resp.ok:
            logger.warning("Slack alert failed: %s %s", resp.status_code, resp.text[:200])
    except Exception:
        logger.debug("Slack alert exception", exc_info=True)


def _send_email_stub(level: str, message: str, data: Optional[Dict[str, Any]]) -> None:
    """Placeholder for email alerting; integrate with SMTP as needed."""
    # Intentionally left as no-op with log; avoids pulling in SMTP deps here.
    logger.info("Email alert stub: %s %s %s", level, message, data)


def send_alert(level: str, message: str, data: Optional[Dict[str, Any]] = None, *, alert_type: Optional[str] = None) -> None:
    """Send an alert to configured channels with rate limiting.

    Parameters:
      - level: "INFO", "WARNING", or "CRITICAL"
      - message: short human-readable description
      - data: optional structured dict with extra context (JSON-serializable)
      - alert_type: identifier for rate limiting (e.g. "drawdown_warning",
        "ws_down", "api_error_rate", "sec_8k", "whale_print", "daily_pnl").
        If None, uses level as the type.
    """
    lvl = level.upper()
    if lvl not in {"INFO", "WARNING", "CRITICAL"}:
        raise ValueError("level must be one of INFO, WARNING, CRITICAL")

    alert_type = alert_type or lvl
    if _rate_limited(alert_type):
        logger.debug("Alert of type '%s' rate-limited; skipping.", alert_type)
        return

    msg = _format_alert_message(lvl, message, data)

    # Always log locally
    if lvl == "CRITICAL":
        logger.critical(msg)
    elif lvl == "WARNING":
        logger.warning(msg)
    else:
        logger.info(msg)

    # Primary channels
    _send_telegram(msg)
    _send_slack(msg)
    _send_email_stub(lvl, message, data)

