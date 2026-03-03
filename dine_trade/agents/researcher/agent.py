"""Fundamental Researcher agent — gemini-3.1-pro-preview (GEMINI_MODEL_RESEARCHER).

Inputs: symbol, optional ohlcv_df, fundamentals dict, SEC filing context.
Output: {"verdict": "APPROVE"|"REJECT", "score": float, "reasoning": str}.
"""
from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd

from dine_trade.config.settings import GEMINI_API_KEY, GEMINI_MODEL_RESEARCHER

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - handled gracefully at runtime
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


RESEARCHER_PROMPT = """You are a Fundamental Researcher for an equity trading desk.

Given company fundamentals and recent SEC filing context for a symbol, decide if the stock
should be considered for a long trade today.

Output exactly in this format (no extra text before or after):
VERDICT: APPROVE or REJECT
SCORE: <number from 1 to 10>
REASONING: <1-3 sentences explaining the fundamental view>

Score 1 = strong avoid, 10 = strong conviction to consider. Be concise and risk-aware."""


def _fundamentals_block(fundamentals: dict[str, Any] | None) -> str:
    if not fundamentals:
        return "No fundamental metrics provided."
    lines: list[str] = []
    for k, v in fundamentals.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines)


def _sec_block(sec_context: str | None) -> str:
    if not sec_context:
        return "No SEC filing context provided."
    return sec_context.strip()


def _ohlcv_block(ohlcv_df: pd.DataFrame | None, symbol: str) -> str:
    if ohlcv_df is None or ohlcv_df.empty:
        return f"No OHLCV data for {symbol}."
    df = ohlcv_df
    close_col = next((c for c in df.columns if str(c).lower() == "close"), df.columns[-1])
    closes = pd.to_numeric(df[close_col], errors="coerce").dropna()
    if closes.empty:
        return f"OHLCV present but no valid closes for {symbol}."
    last_close = closes.iloc[-1]
    min_close = closes.min()
    max_close = closes.max()
    return f"Closes: last={last_close:.2f}, min={min_close:.2f}, max={max_close:.2f}, rows={len(closes)}"


def run_researcher(
    symbol: str,
    ohlcv_df: pd.DataFrame | None = None,
    fundamentals: dict[str, Any] | None = None,
    sec_context: str | None = None,
) -> dict[str, Any]:
    """Run Fundamental Researcher and return verdict, score, reasoning."""
    if not GEMINI_API_KEY:
        return {"verdict": "REJECT", "score": 0.0, "reasoning": "GEMINI_API_KEY not set"}
    if genai is None or types is None:
        return {
            "verdict": "REJECT",
            "score": 0.0,
            "reasoning": "google-genai not installed; pip install google-genai",
        }

    fundamentals_block = _fundamentals_block(fundamentals)
    sec_block = _sec_block(sec_context)
    ohlcv_block = _ohlcv_block(ohlcv_df, symbol)

    user_content = f"""## Symbol
{symbol}

## OHLCV summary
{ohlcv_block}

## Fundamentals
{fundamentals_block}

## SEC filing context
{sec_block}
"""

    try:
        with genai.Client(api_key=GEMINI_API_KEY) as client:
            response = client.models.generate_content(
                model=GEMINI_MODEL_RESEARCHER,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=RESEARCHER_PROMPT,
                    temperature=0.2,
                    max_output_tokens=384,
                ),
            )
        text = (response.text or "").strip()
    except Exception as e:  # pragma: no cover - network / API errors
        logger.exception("Researcher agent Gemini call failed: %s", e)
        return {"verdict": "REJECT", "score": 0.0, "reasoning": str(e)}

    verdict = "REJECT"
    score = 0.0
    reasoning = ""

    verdict_m = re.search(r"VERDICT:\s*(APPROVE|REJECT)", text, re.IGNORECASE)
    if verdict_m:
        verdict = verdict_m.group(1).upper()
        if verdict not in ("APPROVE", "REJECT"):
            verdict = "REJECT"

    score_m = re.search(r"SCORE:\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    if score_m:
        try:
            score = float(score_m.group(1))
            score = max(1.0, min(10.0, score))
        except ValueError:
            score = 0.0

    reason_m = re.search(r"REASONING:\s*(.+?)(?=\n\n|\Z)", text, re.IGNORECASE | re.DOTALL)
    if reason_m:
        reasoning = reason_m.group(1).strip()
    if not reasoning and text:
        reasoning = text[:500]

    return {
        "verdict": verdict,
        "score": float(score),
        "reasoning": reasoning or "No reasoning extracted.",
    }

