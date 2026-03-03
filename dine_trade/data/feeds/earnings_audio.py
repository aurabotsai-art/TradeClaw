"""Earnings call transcript and sentiment analysis.

Data source:
- Financial Modeling Prep (FMP) Earnings Call Transcripts API.

Core functions:
- get_earnings_transcript(symbol, quarter=None) -> str
    Fetch the text of the most recent (or specified) earnings call.

- analyze_transcript_sentiment(transcript: str, *, symbol: str | None = None, quarter: str | None = None, store: bool = True) -> dict
    Use Gemini 3.1 Pro Preview to analyze CEO tone, guidance direction, and
    produce structured sentiment output.

Optional (not wired by default):
- transcribe_audio_with_whisper(audio_path: str) -> str
    Use OpenAI Whisper (if installed) to transcribe an audio file, then pass
    transcript into Gemini for semantic analysis.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

import requests

from dine_trade.config.settings import FMP_API_KEY, GEMINI_API_KEY, GEMINI_MODEL_RESEARCHER
from dine_trade.storage.supabase_client import _get_client as _get_supabase_client  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)

FMP_TRANSCRIPT_URL = "https://financialmodelingprep.com/stable/earning-call-transcript"

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - optional until google-genai installed
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]


def _parse_quarter(quarter: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    """Parse quarter strings like '2024Q1' or '2024-Q1' into (year, q)."""
    if not quarter:
        return None, None
    s = quarter.strip().upper()
    m = re.search(r"(\d{4})\D*Q([1-4])", s)
    if not m:
        return None, None
    year = int(m.group(1))
    q = int(m.group(2))
    return year, q


def get_earnings_transcript(symbol: str, quarter: Optional[str] = None) -> str:
    """Fetch earnings call transcript text for symbol.

    - If quarter is provided in 'YYYYQn' form, requests that specific call.
    - Otherwise, requests the latest available transcript.
    """
    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY not set; cannot fetch earnings transcripts.")
        return ""

    params: Dict[str, Any] = {"symbol": symbol.upper(), "apikey": FMP_API_KEY}
    year, q = _parse_quarter(quarter)
    if year is not None and q is not None:
        params["year"] = year
        params["quarter"] = q

    try:
        resp = requests.get(FMP_TRANSCRIPT_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:  # pragma: no cover - network/API errors
        logger.warning("Failed to fetch earnings transcript for %s: %s", symbol, e)
        return ""

    # API may return a list of transcripts; take the first.
    if isinstance(data, list) and data:
        t = data[0]
    elif isinstance(data, dict):
        t = data
    else:
        return ""

    # Common FMP field names: 'content' or 'transcript'
    transcript = t.get("content") or t.get("transcript") or ""
    if not isinstance(transcript, str):
        return ""
    return transcript


EARNINGS_SENTIMENT_PROMPT = """You are an equity analyst specializing in earnings call analysis.

Given an earnings call transcript, analyze CEO tone and guidance sentiment.

Respond ONLY with valid JSON using this schema:
{
  "tone": "<overall tone: POSITIVE | NEUTRAL | NEGATIVE>",
  "guidance_direction": "<RAISED | LOWERED | MAINTAINED | MIXED | UNSPECIFIED>",
  "confidence_score": <number 1-10>,
  "red_flags": ["<short phrase>", "..."],
  "green_flags": ["<short phrase>", "..."]
}

Focus on:
- CEO tone and confidence level
- Guidance: raised, lowered, or maintained vs prior expectations
- Mentions of headwinds vs tailwinds
- Specific phrases signaling concern (red_flags) or strength (green_flags)

Do NOT include any extra keys or text outside this JSON object."""


def _insert_earnings_analysis(row: Dict[str, Any]) -> None:
    """Best-effort insert into Supabase earnings_analysis table."""
    try:
        client = _get_supabase_client()
    except Exception:
        return
    try:
        client.table("earnings_analysis").insert(row).execute()
    except Exception:
        logger.debug("Supabase earnings_analysis insert failed", exc_info=True)


def analyze_transcript_sentiment(
    transcript: str,
    *,
    symbol: Optional[str] = None,
    quarter: Optional[str] = None,
    store: bool = True,
) -> Dict[str, Any]:
    """Analyze an earnings call transcript with Gemini 3.1 Pro.

    Returns dict:
        {
          "tone": str,
          "guidance_direction": str,
          "confidence_score": float,
          "red_flags": list[str],
          "green_flags": list[str],
        }
    """
    if not transcript:
        return {
            "tone": "UNSPECIFIED",
            "guidance_direction": "UNSPECIFIED",
            "confidence_score": 0.0,
            "red_flags": [],
            "green_flags": [],
        }

    if not GEMINI_API_KEY or genai is None or types is None:
        logger.warning("Gemini API not configured; returning empty sentiment result.")
        return {
            "tone": "UNSPECIFIED",
            "guidance_direction": "UNSPECIFIED",
            "confidence_score": 0.0,
            "red_flags": [],
            "green_flags": [],
        }

    user_content = transcript

    try:
        with genai.Client(api_key=GEMINI_API_KEY) as client:
            response = client.models.generate_content(
                model=GEMINI_MODEL_RESEARCHER,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=EARNINGS_SENTIMENT_PROMPT,
                    temperature=0.2,
                    max_output_tokens=512,
                    response_mime_type="application/json",
                ),
            )
        text = (response.text or "").strip()
    except Exception as e:  # pragma: no cover
        logger.exception("Gemini earnings sentiment call failed: %s", e)
        return {
            "tone": "UNSPECIFIED",
            "guidance_direction": "UNSPECIFIED",
            "confidence_score": 0.0,
            "red_flags": [],
            "green_flags": [],
            "error": str(e),
        }

    result: Dict[str, Any]
    try:
        result = json.loads(text)
    except Exception:
        logger.debug("Failed to parse Gemini JSON; raw text=%s", text[:500])
        # Best-effort fallback
        result = {
            "tone": "UNSPECIFIED",
            "guidance_direction": "UNSPECIFIED",
            "confidence_score": 0.0,
            "red_flags": [],
            "green_flags": [],
            "raw_text": text,
        }

    # Normalize types and fill defaults
    tone = str(result.get("tone", "UNSPECIFIED"))
    guidance_direction = str(result.get("guidance_direction", "UNSPECIFIED"))
    try:
        confidence_score = float(result.get("confidence_score", 0.0) or 0.0)
    except (TypeError, ValueError):
        confidence_score = 0.0
    red_flags = result.get("red_flags") or []
    green_flags = result.get("green_flags") or []

    out = {
        "symbol": symbol,
        "quarter": quarter,
        "tone": tone,
        "guidance_direction": guidance_direction,
        "confidence_score": confidence_score,
        "red_flags": red_flags,
        "green_flags": green_flags,
    }

    if store and symbol:
        row = {
            "symbol": symbol,
            "quarter": quarter,
            "tone": tone,
            "guidance_direction": guidance_direction,
            "confidence_score": confidence_score,
            "red_flags": red_flags,
            "green_flags": green_flags,
        }
        _insert_earnings_analysis(row)

    return out


def transcribe_audio_with_whisper(audio_path: str) -> str:
    """Transcribe an audio file using OpenAI Whisper (if installed).

    This is optional and not wired into any pipeline by default.
    """
    try:
        import whisper  # type: ignore[import]
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "openai-whisper is not installed; run `pip install openai-whisper`."
        ) from e

    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    text = result.get("text") or ""
    return text

