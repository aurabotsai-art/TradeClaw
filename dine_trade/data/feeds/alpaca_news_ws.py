"""Alpaca News WebSocket — live news stream feeding Sentiment Agent and storage.

Uses alpaca-py `NewsDataStream` (or alpaca-trade-api fallback) to stream news:

- Pushes raw news JSON into Redis list `news:live` (if Redis configured).
- Optionally triggers Sentiment Agent rescans for symbols in our universe.
- Stores news + sentiment into Supabase `news_log` table.

This module is designed as an async entrypoint:

    python -m dine_trade.data.feeds.alpaca_news_ws

Environment/config:
- APCA_API_KEY_ID / APCA_API_SECRET_KEY from config.settings
- Optional: REDIS_URL for Redis
- Supabase URL/key for news_log persistence (via storage.supabase_client)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Iterable, List, Sequence

from dine_trade.config.settings import APCA_API_KEY_ID, APCA_API_SECRET_KEY, UNIVERSE_DEFAULT
from dine_trade.storage.redis_client import _get_client as _get_redis_client  # type: ignore[attr-defined]
from dine_trade.storage.supabase_client import _get_client as _get_supabase_client  # type: ignore[attr-defined]
from dine_trade.agents.sentiment import run_sentiment_agent
from dine_trade.data.feeds import get_recent_headlines

logger = logging.getLogger(__name__)

try:
    # Prefer alpaca.data.live NewsDataStream if available (alpaca-py)
    from alpaca.data.live import NewsDataStream  # type: ignore[import]
except ImportError:  # pragma: no cover - optional dependency
    try:
        # Fallback: alpaca_trade_api (older SDK)
        from alpaca_trade_api.stream import NewsDataStream  # type: ignore[no-redef,import]
    except ImportError:
        NewsDataStream = None  # type: ignore[assignment]


def _redis_rpush(key: str, value: str) -> None:
    """Best-effort push into Redis list; no-op if Redis not configured."""
    try:
        client = _get_redis_client()
    except Exception:
        return
    try:
        client.rpush(key, value)
    except Exception:
        # Do not raise from streaming path
        logger.debug("Redis rpush failed for key=%s", key, exc_info=True)


def _supabase_insert_news(row: Dict[str, Any]) -> None:
    """Best-effort insert into Supabase news_log; no-op if not configured."""
    try:
        client = _get_supabase_client()
    except Exception:
        return
    try:
        client.table("news_log").insert(row).execute()
    except Exception:
        logger.debug("Supabase news_log insert failed", exc_info=True)


def _extract_symbols(news: Any) -> List[str]:
    """Extract list of symbols from news event."""
    syms: Sequence[str] = getattr(news, "symbols", []) or []
    return [s.upper() for s in syms]


async def trigger_sentiment_rescan(symbol: str) -> Dict[str, Any]:
    """Fetch recent headlines and run Sentiment Agent once for symbol.

    This is a simple hook that could later be expanded to push signals into
    a queue or notify an orchestration layer.
    """
    headlines = get_recent_headlines(symbol, limit=20)
    result = run_sentiment_agent(symbol, headlines)
    logger.info(
        "Sentiment rescan for %s: verdict=%s score=%.2f",
        symbol,
        result.get("verdict"),
        float(result.get("score", 0.0) or 0.0),
    )
    # Optionally, persist sentiment snapshot alongside news_log elsewhere.
    return result


async def _handle_news_event(news: Any, universe: Iterable[str]) -> None:
    """Core handler for incoming news events."""
    # Normalize to dict for storage/logging
    try:
        # alpaca-py models typically have .model_dump_json() / .dict()
        if hasattr(news, "model_dump_json"):
            raw_json = news.model_dump_json()
            payload = json.loads(raw_json)
        elif hasattr(news, "dict"):
            payload = news.dict()  # type: ignore[call-arg]
            raw_json = json.dumps(payload)
        elif hasattr(news, "json"):
            raw_json = news.json()  # type: ignore[call-arg]
            payload = json.loads(raw_json)
        else:
            # Last resort: best-effort repr
            payload = {
                "headline": getattr(news, "headline", ""),
                "summary": getattr(news, "summary", ""),
                "symbols": list(getattr(news, "symbols", []) or []),
                "created_at": str(getattr(news, "created_at", "")),
            }
            raw_json = json.dumps(payload)
    except Exception:
        logger.debug("Failed to normalize news event", exc_info=True)
        return

    # 1) Push raw news into Redis stream/list
    _redis_rpush("news:live", raw_json)

    # 2) If symbol intersects universe, trigger Sentiment rescan
    symbols = _extract_symbols(news)
    universe_set = {s.upper() for s in universe}
    trigger_syms = [s for s in symbols if s in universe_set]

    sentiment_result: Dict[str, Any] | None = None
    if trigger_syms:
        # For now, rescan per primary symbol (first in trigger_syms)
        primary = trigger_syms[0]
        try:
            sentiment_result = await trigger_sentiment_rescan(primary)
        except Exception:
            logger.exception("Sentiment rescan failed for %s", primary)

    # 3) Best-effort Supabase persistence (headline, symbols, sentiment, created_at)
    try:
        row: Dict[str, Any] = {
            "headline": payload.get("headline") or "",
            "summary": payload.get("summary") or "",
            "symbols": payload.get("symbols") or symbols,
            "created_at": payload.get("created_at") or payload.get("updated_at"),
        }
        if sentiment_result is not None:
            row["sentiment_score"] = float(sentiment_result.get("score", 0.0) or 0.0)
            row["sentiment_verdict"] = sentiment_result.get("verdict")
            row["sentiment_reason"] = sentiment_result.get("reasoning")
        _supabase_insert_news(row)
    except Exception:
        logger.debug("Failed to build/insert news_log row", exc_info=True)


async def run_news_stream(universe: Iterable[str] | None = None) -> None:
    """Run Alpaca NewsDataStream and process live news.

    - universe: iterable of symbols to watch (defaults to UNIVERSE_DEFAULT).
    """
    if NewsDataStream is None:
        raise RuntimeError("NewsDataStream not available; install alpaca-py or alpaca-trade-api.")

    if not APCA_API_KEY_ID or not APCA_API_SECRET_KEY:
        raise RuntimeError("APCA_API_KEY_ID / APCA_API_SECRET_KEY must be set for Alpaca news stream.")

    if universe is None:
        universe = UNIVERSE_DEFAULT
    universe = list(universe)

    logger.info("Starting Alpaca NewsDataStream for universe=%s", list(universe))

    # alpaca-py NewsDataStream is async, but older alpaca_trade_api uses callbacks + .run()
    client = NewsDataStream(APCA_API_KEY_ID, APCA_API_SECRET_KEY)

    async def _handler(news: Any) -> None:
        await _handle_news_event(news, universe)

    # Subscribe to news for the universe (or * if empty)
    sub_symbols: List[str] = list(universe) if universe else ["*"]
    client.subscribe_news(_handler, *sub_symbols)

    # Run the client; this typically blocks until cancelled.
    await client.run()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        asyncio.run(run_news_stream())
    except KeyboardInterrupt:
        logger.info("News stream interrupted by user.")

