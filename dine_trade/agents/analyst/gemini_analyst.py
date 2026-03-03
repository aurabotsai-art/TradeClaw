"""Phase 1 single analyst: gemini-3.1-pro-preview (GEMINI_MODEL_RESEARCHER) for conviction score."""
from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd

from dine_trade.config.settings import GEMINI_API_KEY, GEMINI_MODEL_RESEARCHER

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

logger = logging.getLogger(__name__)


def _ohlcv_summary(ohlcv_df: pd.DataFrame, symbol: str) -> str:
    """Build a short text summary of OHLCV for the prompt."""
    if ohlcv_df is None or ohlcv_df.empty:
        return f"No OHLCV data for {symbol}."
    df = ohlcv_df
    # Prefer standard names (lowercase or capitalized)
    open_col = next((c for c in df.columns if str(c).lower() == "open"), df.columns[0])
    high_col = next((c for c in df.columns if str(c).lower() == "high"), None)
    low_col = next((c for c in df.columns if str(c).lower() == "low"), None)
    close_col = next((c for c in df.columns if str(c).lower() == "close"), None)
    vol_col = next((c for c in df.columns if "vol" in str(c).lower()), None)

    parts = [f"Symbol: {symbol}", f"Rows: {len(df)}"]
    if close_col is not None and close_col in df.columns:
        close_series = pd.to_numeric(df[close_col], errors="coerce").dropna()
        if not close_series.empty:
            parts.append(f"Close: last={close_series.iloc[-1]:.2f}, min={close_series.min():.2f}, max={close_series.max():.2f}")
    if open_col is not None and open_col in df.columns:
        open_series = pd.to_numeric(df[open_col], errors="coerce").dropna()
        if not open_series.empty:
            parts.append(f"Open: last={open_series.iloc[-1]:.2f}")
    if high_col is not None and high_col in df.columns:
        high_series = pd.to_numeric(df[high_col], errors="coerce").dropna()
        if not high_series.empty:
            parts.append(f"High (period): {high_series.max():.2f}")
    if low_col is not None and low_col in df.columns:
        low_series = pd.to_numeric(df[low_col], errors="coerce").dropna()
        if not low_series.empty:
            parts.append(f"Low (period): {low_series.min():.2f}")
    if vol_col is not None and vol_col in df.columns:
        vol_series = pd.to_numeric(df[vol_col], errors="coerce").dropna()
        if not vol_series.empty:
            parts.append(f"Volume: last={vol_series.iloc[-1]:.0f}, avg={vol_series.mean():.0f}")
    return "\n".join(parts)


def _headlines_text(headlines: list[dict[str, Any]]) -> str:
    """Format headlines for the prompt."""
    if not headlines:
        return "No recent headlines."
    lines = []
    for i, h in enumerate(headlines[:20], 1):
        title = h.get("title") or ""
        pub = h.get("published_at") or ""
        src = h.get("source") or ""
        lines.append(f"{i}. [{pub}] {title} (source: {src})")
    return "\n".join(lines)


CONVICTION_PROMPT = """You are a trading analyst. Given OHLCV summary and recent headlines for a symbol, output a conviction score and short reasoning.

Output exactly in this format (no other text before or after):
SCORE: <number from 1 to 10>
REASONING: <1-3 sentences>

Score 1 = strong avoid, 10 = strong conviction to consider. Be concise."""


def get_conviction_score(
    ohlcv_df: pd.DataFrame,
    headlines: list[dict[str, Any]],
    symbol: str,
) -> tuple[float, str]:
    """
    Phase 1 single analyst: use GEMINI_MODEL_RESEARCHER (gemini-3.1-pro-preview).
    Returns (score 1–10, reasoning string). On error returns (0.0, error message).
    """
    if not GEMINI_API_KEY:
        return 0.0, "GEMINI_API_KEY not set"
    if genai is None or types is None:
        return 0.0, "google-genai not installed; pip install google-genai"

    ohlcv_summary = _ohlcv_summary(ohlcv_df, symbol)
    headlines_block = _headlines_text(headlines)
    user_content = f"""## OHLCV summary
{ohlcv_summary}

## Recent headlines
{headlines_block}

Provide SCORE (1-10) and REASONING for {symbol}."""

    try:
        with genai.Client(api_key=GEMINI_API_KEY) as client:
            response = client.models.generate_content(
                model=GEMINI_MODEL_RESEARCHER,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=CONVICTION_PROMPT,
                    temperature=0.2,
                    max_output_tokens=256,
                ),
            )
        text = (response.text or "").strip()
    except Exception as e:
        logger.exception("Gemini conviction call failed: %s", e)
        return 0.0, str(e)

    # Parse SCORE and REASONING
    score = 0.0
    reasoning = ""

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

    return score, reasoning or "No reasoning extracted."
