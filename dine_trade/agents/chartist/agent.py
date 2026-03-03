"""Chartist agent (Technical) using Gemini flash (GEMINI_MODEL_FAST).

Inputs:
  - symbol: ticker string, e.g. "NVDA"
  - ohlcv_df: pandas.DataFrame with at least columns: "date", "open", "high",
    "low", "close", "volume"

Outputs (dict):
  {
    "verdict": "APPROVE" | "REJECT",
    "score": float (1-10),
    "reasoning": str
  }
"""
from __future__ import annotations

import json
from typing import Any, Dict

import numpy as np
import pandas as pd

from dine_trade.config.settings import GEMINI_API_KEY, GEMINI_MODEL_FAST

try:
    from google import genai
    from google.genai import types
except ImportError:  # pragma: no cover - handled gracefully in run_chartist
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]


def _compute_indicators(ohlcv_df: pd.DataFrame) -> Dict[str, Any]:
    """Compute RSI(14), MACD(12,26,9), 20/50 MAs, basic trend flags."""
    df = ohlcv_df.copy().sort_values("date")
    close = df["close"].astype(float)

    # Simple moving averages
    df["ma20"] = close.rolling(window=20, min_periods=5).mean()
    df["ma50"] = close.rolling(window=50, min_periods=10).mean()

    # RSI(14)
    delta = close.diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(gain).rolling(window=14, min_periods=5).mean()
    roll_down = pd.Series(loss).rolling(window=14, min_periods=5).mean()
    rs = roll_up / (roll_down.replace(0, np.nan))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    df["rsi14"] = rsi

    # MACD (12,26,9) using EMAs
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal_line
    df["macd"] = macd_line
    df["macd_signal"] = signal_line
    df["macd_hist"] = hist

    last = df.iloc[-1]
    recent = df.tail(60).copy()
    # Ensure date is JSON-serializable
    if "date" in recent.columns:
        recent["date"] = recent["date"].astype(str)
    recent = recent[
        ["date", "close", "rsi14", "ma20", "ma50", "macd", "macd_signal", "macd_hist"]
    ]

    trend: str
    if last["ma20"] > last["ma50"]:
        trend = "short_term_uptrend (ma20 > ma50)"
    elif last["ma20"] < last["ma50"]:
        trend = "short_term_downtrend (ma20 < ma50)"
    else:
        trend = "flat (ma20 ~ ma50)"

    return {
        "latest": {
            "date": str(last["date"]),
            "close": float(last["close"]),
            "rsi14": float(last.get("rsi14", np.nan)),
            "ma20": float(last.get("ma20", np.nan)),
            "ma50": float(last.get("ma50", np.nan)),
            "macd": float(last.get("macd", np.nan)),
            "macd_signal": float(last.get("macd_signal", np.nan)),
            "macd_hist": float(last.get("macd_hist", np.nan)),
            "trend": trend,
        },
        "recent_sample": recent.to_dict(orient="records"),
    }


def _build_prompt(symbol: str, indicators: Dict[str, Any]) -> str:
    return (
        "You are a Technical Chartist in a risk-first trading system.\n\n"
        f"Symbol: {symbol}\n\n"
        "You are given recent daily OHLCV-derived indicators:\n"
        f"{json.dumps(indicators, indent=2)}\n\n"
        "Task:\n"
        "- Analyze RSI(14), MACD(12,26,9), 20/50-day moving averages, and price action.\n"
        "- Consider whether the chart shows trend, momentum, or mean-reversion opportunity.\n"
        "- Be conservative; only APPROVE when there is a clear, high-probability technical edge.\n\n"
        "Respond strictly as a single JSON object with keys:\n"
        '{\n'
        '  "verdict": "APPROVE" or "REJECT",\n'
        '  "score": number between 1 and 10,\n'
        '  "reasoning": short explanation\n'
        "}\n"
        "Do not include any extra text outside JSON.\n"
    )


def _parse_response(text: str) -> Dict[str, Any]:
    """Parse Gemini text into {verdict, score, reasoning}."""
    raw = text.strip()
    # Strip code fences if present
    if raw.startswith("```"):
        raw = raw.strip("`")
        # remove optional leading language tag
        first_newline = raw.find("\n")
        if first_newline != -1:
            raw = raw[first_newline + 1 :]
    try:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Try to find the first { and last } as a fallback
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                data = json.loads(raw[start : end + 1])
            else:
                raise

        verdict = str(data.get("verdict", "")).upper()
        if verdict not in ("APPROVE", "REJECT"):
            verdict = "REJECT"
        try:
            score = float(data.get("score", 0.0))
        except (TypeError, ValueError):
            score = 0.0
        reasoning = str(data.get("reasoning", "")).strip()
        return {"verdict": verdict, "score": score, "reasoning": reasoning}
    except Exception:
        # If the model didn't return valid JSON, fail closed with the raw text
        return {
            "verdict": "REJECT",
            "score": 0.0,
            "reasoning": raw[:500],
        }


def run_chartist(symbol: str, ohlcv_df: pd.DataFrame) -> Dict[str, Any]:
    """Run the Chartist agent.

    :param symbol: Ticker symbol, e.g. \"NVDA\".
    :param ohlcv_df: DataFrame with OHLCV data.
    :return: dict with verdict, score, reasoning.
    """
    if ohlcv_df is None or ohlcv_df.empty:
        raise ValueError("ohlcv_df must be a non-empty DataFrame for Chartist agent.")

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

    indicators = _compute_indicators(ohlcv_df)
    prompt = _build_prompt(symbol, indicators)

    try:
        with genai.Client(api_key=GEMINI_API_KEY) as client:
            response = client.models.generate_content(
                model=GEMINI_MODEL_FAST,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=384,
                ),
            )
        text = response.text or ""
    except Exception as e:  # pragma: no cover - network / API errors
        return {
            "verdict": "REJECT",
            "score": 0.0,
            "reasoning": str(e),
        }

    parsed = _parse_response(text)
    return parsed

