from __future__ import annotations

"""
SEC EDGAR real-time watcher.

Features:
  - watch_filings(symbols, form_types)  -> long-running poller (every 5 minutes)
  - parse_filing_summary(filing_url)    -> dict using Gemini 3.1 Pro (researcher model)

Behavior:
  - Uses EDGAR full-text/Company RSS to detect new filings for the watched
    symbols and configured form types (8-K, 10-K, 10-Q, SC 13G, SC 13D).
  - On new 8-K: immediately trigger a Researcher Agent rescan for that symbol
    (hook point provided for integration).
  - Stores parsed summaries in Supabase `sec_filings` table.

NOTE:
  - This module is designed for backend/offline use. It should be run in a
    dedicated process or task scheduler, not inside a latency-sensitive path.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib.parse import urlencode

import feedparser
import requests

from dine_trade.config.settings import GEMINI_API_KEY, GEMINI_MODEL_RESEARCHER
from dine_trade.storage.redis_client import _get_client as _get_redis_client
from dine_trade.storage.supabase_client import _get_client as _get_supabase_client

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover - optional at import time
    genai = None
    genai_types = None

logger = logging.getLogger(__name__)


USER_AGENT = (
    "DineTradeBot/1.0 (EDGAR watcher; "
    "contact: your-email@example.com)"
)


def _sec_headers() -> Dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/atom+xml,application/xml;q=0.9,*/*;q=0.8",
    }


def _edgar_rss_url(ticker: str, form_types: Sequence[str]) -> str:
    """
    Build an EDGAR company feed URL for given ticker and form types.

    This uses the legacy browse-edgar feed, which is still widely available.
    """
    # SEC expects uppercase ticker/CIK in query
    params = {
        "action": "getcompany",
        "CIK": ticker.upper(),
        "type": " ".join(form_types),
        "owner": "exclude",
        "count": "40",
        "output": "atom",
    }
    return f"https://www.sec.gov/cgi-bin/browse-edgar?{urlencode(params)}"


def _load_seen_filings() -> Dict[str, str]:
    """
    Load previously seen filing IDs from Redis.

    We store a simple string set in Redis under key `sec_filings:seen`.
    """
    try:
        client = _get_redis_client()
    except RuntimeError:
        return {}

    key = "sec_filings:seen"
    ids = client.smembers(key)
    out: Dict[str, str] = {}
    for b in ids:
        try:
            s = b.decode("utf-8")
        except Exception:
            continue
        out[s] = s
    return out


def _mark_filing_seen(filing_id: str) -> None:
    """Mark a filing as seen in Redis."""
    try:
        client = _get_redis_client()
    except RuntimeError:
        return
    key = "sec_filings:seen"
    client.sadd(key, filing_id)


def _download_text(url: str) -> str:
    """Download filing text/HTML from EDGAR."""
    try:
        resp = requests.get(url, headers=_sec_headers(), timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception as e:  # pragma: no cover - network/API issues
        logger.warning("Failed to download EDGAR filing from %s: %s", url, e)
        return ""


def parse_filing_summary(filing_url: str) -> Dict[str, Any]:
    """
    Download SEC filing and extract structured summary using Gemini 3.1 Pro.

    Returns:
        {
          "event_type": str,
          "financial_impact": str,
          "sentiment": "positive"|"negative"|"neutral"|"...",
          "guidance_changes": str,
          "raw_summary": str,
        }
    """
    text = _download_text(filing_url)
    if not text:
        return {
            "event_type": "",
            "financial_impact": "",
            "sentiment": "unknown",
            "guidance_changes": "",
            "raw_summary": "",
        }

    if not GEMINI_API_KEY or genai is None or genai_types is None:
        # Fallback: naive text truncation with labels.
        snippet = text[:4000]
        return {
            "event_type": "unknown",
            "financial_impact": "unknown",
            "sentiment": "unknown",
            "guidance_changes": "unknown",
            "raw_summary": snippet,
        }

    system_instruction = (
        "You are a securities filing analysis expert.\n"
        "Given an SEC filing text, extract:\n"
        "1) event type (e.g. earnings, M&A, management change, guidance update),\n"
        "2) expected financial impact (concise),\n"
        "3) sentiment (one of: positive, negative, neutral),\n"
        "4) any forward guidance changes.\n\n"
        "Respond in this exact JSON format and nothing else:\n"
        '{\"event_type\": \"...\", \"financial_impact\": \"...\", '
        '\"sentiment\": \"positive|negative|neutral\", '
        '\"guidance_changes\": \"...\", \"raw_summary\": \"short plain-English summary\"}'
    )

    contents = text[:30_000]  # keep under token limits

    try:
        with genai.Client(api_key=GEMINI_API_KEY) as client:
            response = client.models.generate_content(
                model=GEMINI_MODEL_RESEARCHER,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1,
                    max_output_tokens=512,
                ),
            )
        resp_text = (response.text or "").strip()
    except Exception as e:  # pragma: no cover
        logger.exception("Gemini SEC filing summary failed: %s", e)
        return {
            "event_type": "unknown",
            "financial_impact": "unknown",
            "sentiment": "unknown",
            "guidance_changes": "unknown",
            "raw_summary": text[:4000],
        }

    import json

    try:
        summary = json.loads(resp_text)
        if not isinstance(summary, dict):
            raise ValueError("Non-dict JSON")
    except Exception:
        # Fallback: wrap raw model text
        summary = {
            "event_type": "unknown",
            "financial_impact": "unknown",
            "sentiment": "unknown",
            "guidance_changes": "unknown",
            "raw_summary": resp_text or text[:4000],
        }

    return summary


def _insert_sec_filing_row(
    symbol: str,
    form_type: str,
    filing_id: str,
    filing_url: str,
    filed_at: datetime,
    summary: Dict[str, Any],
) -> None:
    """Insert parsed filing summary into Supabase sec_filings table."""
    try:
        client = _get_supabase_client()
    except RuntimeError:
        # Supabase not configured; skip persistence
        logger.warning("Supabase not configured; skipping sec_filings insert.")
        return

    row = {
        "symbol": symbol.upper(),
        "form_type": form_type,
        "filing_id": filing_id,
        "filing_url": filing_url,
        "filed_at": filed_at.replace(tzinfo=timezone.utc).isoformat(),
        "event_type": summary.get("event_type"),
        "financial_impact": summary.get("financial_impact"),
        "sentiment": summary.get("sentiment"),
        "guidance_changes": summary.get("guidance_changes"),
        "raw_summary": summary.get("raw_summary"),
    }
    client.table("sec_filings").insert(row).execute()


def _trigger_researcher_rescan(symbol: str) -> None:
    """
    Hook for triggering Researcher Agent rescan when a high-priority filing appears.

    In a full system this might enqueue a job into a task queue (e.g. Redis,
    Celery, or Supabase functions). Here we log the intent; integration can
    be added later.
    """
    logger.info("New 8-K detected for %s — trigger Researcher Agent rescan.", symbol.upper())
    # TODO: integrate with orchestration or background job system.


def _process_feed_for_symbol(
    symbol: str,
    form_types: Sequence[str],
    seen: Dict[str, str],
) -> None:
    """Fetch and process EDGAR RSS feed for a single symbol."""
    url = _edgar_rss_url(symbol, form_types)
    try:
        logger.debug("Fetching EDGAR RSS for %s: %s", symbol, url)
        resp = requests.get(url, headers=_sec_headers(), timeout=30)
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to fetch EDGAR RSS for %s: %s", symbol, e)
        return

    entries = feed.entries or []
    for entry in entries:
        filing_id = entry.get("id") or entry.get("link")
        if not filing_id:
            continue
        if filing_id in seen:
            continue

        title = entry.get("title", "")
        # Try to infer form type from title (e.g. "8-K - XYZ Corp")
        form_type = ""
        for ft in form_types:
            if ft in title:
                form_type = ft
                break
        if not form_type:
            # Last resort: use the first token of title
            form_type = title.split()[0] if title else "UNKNOWN"

        filing_url = entry.get("link") or ""
        filed_at_str = entry.get("updated") or entry.get("published") or ""
        try:
            filed_at = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)  # type: ignore[attr-defined]
        except Exception:
            filed_at = datetime.now(timezone.utc)

        logger.info("New SEC filing for %s: %s (%s) %s", symbol.upper(), form_type, filing_id, filing_url)

        summary = parse_filing_summary(filing_url) if filing_url else {}

        _insert_sec_filing_row(
            symbol=symbol,
            form_type=form_type,
            filing_id=filing_id,
            filing_url=filing_url,
            filed_at=filed_at,
            summary=summary,
        )

        if form_type == "8-K":
            _trigger_researcher_rescan(symbol)

        _mark_filing_seen(filing_id)


def watch_filings(
    symbols: Iterable[str],
    form_types: Optional[Sequence[str]] = None,
    poll_interval_seconds: int = 300,
) -> None:
    """
    Poll EDGAR RSS every `poll_interval_seconds` for new filings.

    Args:
        symbols: iterable of stock tickers (e.g. ['NVDA', 'AAPL']).
        form_types: SEC form types to watch; defaults to:
            ["8-K", "10-K", "10-Q", "SC 13G", "SC 13D"]
        poll_interval_seconds: typically 300 (5 minutes).

    This function runs an infinite loop; run it in a dedicated worker process.
    """
    if form_types is None:
        form_types = ["8-K", "10-K", "10-Q", "SC 13G", "SC 13D"]

    symbols_list: List[str] = [s.upper() for s in symbols]
    logger.info("Starting SEC EDGAR watcher for symbols=%s, forms=%s", symbols_list, form_types)

    while True:
        seen = _load_seen_filings()
        for sym in symbols_list:
            _process_feed_for_symbol(sym, form_types, seen)
        time.sleep(poll_interval_seconds)

