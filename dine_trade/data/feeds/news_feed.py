"""Minimal news headlines: FMP (primary) or NewsAPI fallback. Keys: title, published_at, source."""
from __future__ import annotations

import logging
from typing import Any

import requests

from dine_trade.config.settings import FMP_API_KEY

logger = logging.getLogger(__name__)

FMP_STOCK_NEWS_URL = "https://financialmodelingprep.com/api/v3/stock_news"


def get_recent_headlines(symbol: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Fetch recent headlines for a symbol. Uses FMP Stock News API.
    Returns list of dicts with keys: title, published_at, source.
    """
    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY not set; returning empty headlines")
        return []

    params: dict[str, Any] = {
        "tickers": symbol,
        "limit": min(limit, 50),
        "apikey": FMP_API_KEY,
    }
    try:
        resp = requests.get(FMP_STOCK_NEWS_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.HTTPError as e:
        logger.warning("FMP stock news HTTP %s: %s", getattr(e.response, "status_code", ""), e)
        return []
    except requests.RequestException as e:
        logger.warning("FMP stock news request failed: %s", e)
        return []

    if not isinstance(data, list):
        return []

    out: list[dict[str, Any]] = []
    for item in data[:limit]:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        # FMP: publishedDate is ISO string or "YYYY-MM-DD HH:MM:SS"
        published = item.get("publishedDate") or item.get("date") or ""
        source = item.get("site") or item.get("source") or item.get("author") or ""
        out.append({
            "title": title,
            "published_at": published,
            "source": source,
        })
    return out
