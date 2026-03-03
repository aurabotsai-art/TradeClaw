"""Sentiment Agent (Newsroom) — Gemini flash via GEMINI_MODEL_FAST.

Returns dict:
    {
        "verdict": "APPROVE" | "REJECT",
        "score": float,  # 1–10 sentiment score
        "reasoning": str,
    }
"""
from __future__ import annotations

import logging
import re
from typing import Any

from dine_trade.config.settings import GEMINI_API_KEY, GEMINI_MODEL_FAST

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - optional dependency
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _headlines_text(headlines: list[dict[str, Any]]) -> str:
    """Format headlines for the prompt."""
    if not headlines:
        return "No recent headlines."
    lines: list[str] = []
    for i, h in enumerate(headlines[:20], 1):
        title = h.get("title") or ""
        pub = h.get("published_at") or ""
        src = h.get("source") or ""
        lines.append(f"{i}. [{pub}] {title} (source: {src})")
    return "\n".join(lines)


SENTIMENT_PROMPT = """You are a Sentiment Analyst in a trading newsroom.
Given recent news headlines for a stock, analyze overall sentiment for short- to medium-term trading.

Output exactly in this format (no other text before or after):
VERDICT: <APPROVE or REJECT>
SCORE: <number from 1 to 10>
REASONING: <1-3 sentences>

Interpretation:
- VERDICT=APPROVE if overall news sentiment is supportive/constructive for a potential long trade.
- VERDICT=REJECT if sentiment is negative, highly uncertain, or too noisy.
- SCORE 1 = very negative, 10 = very positive. Be concise."""


def run_sentiment_agent(
    symbol: str,
    headlines: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run high-speed sentiment analysis on news headlines for symbol.

    Inputs:
        symbol: Ticker symbol (e.g. "NVDA").
        headlines: List of dicts with keys title, published_at, source.

    Returns:
        {"verdict": "APPROVE"|"REJECT", "score": float, "reasoning": str}
    """
    # Fails closed if Gemini is not available
    if not GEMINI_API_KEY:
        return {
            "verdict": "REJECT",
            "score": 0.0,
            "reasoning": "GEMINI_API_KEY not set",
        }
    if genai is None or types is None:
        return {
            "verdict": "REJECT",
            "score": 0.0,
            "reasoning": "google-genai not installed; pip install google-genai",
        }

    headlines_block = _headlines_text(headlines)
    user_content = f"""## Symbol
{symbol}

## Recent headlines
{headlines_block}

Provide VERDICT, SCORE 1-10, and brief REASONING for {symbol}."""

    try:
        with genai.Client(api_key=GEMINI_API_KEY) as client:
            response = client.models.generate_content(
                model=GEMINI_MODEL_FAST,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=SENTIMENT_PROMPT,
                    temperature=0.3,
                    max_output_tokens=256,
                ),
            )
        text = (response.text or "").strip()
    except Exception as e:  # pragma: no cover - network / API errors
        logger.exception("Sentiment agent Gemini call failed: %s", e)
        return {
            "verdict": "REJECT",
            "score": 0.0,
            "reasoning": str(e),
        }

    verdict = "REJECT"
    score = 0.0
    reasoning = ""

    verdict_m = re.search(r"VERDICT:\s*(APPROVE|REJECT)", text, re.IGNORECASE)
    if verdict_m:
        verdict = verdict_m.group(1).upper()

    score_m = re.search(r"SCORE:\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if score_m:
        try:
            score = float(score_m.group(1))
            score = max(1.0, min(10.0, score))
        except ValueError:
            pass

    reason_m = re.search(r"REASONING:\s*(.+?)(?=\n\n|\Z)", text, re.IGNORECASE | re.DOTALL)
    if reason_m:
        reasoning = reason_m.group(1).strip()
    if not reasoning and text:
        reasoning = text[:500]

    return {
        "verdict": verdict,
        "score": score,
        "reasoning": reasoning or "No reasoning extracted.",
    }

