"""
Phase 1 paper script: Fetch OHLCV and headlines; 20-day MA and price_vs_ma_allowed;
Gemini get_conviction_score. Before any order: DataValidator (bars vs quote mid);
if score > 8 and MA and DataValidator pass: smart_limit_order("NVDA", "buy", qty, 60).
Log to console and logs/phase1_YYYYMMDD.log.
"""
# Run from project root: python scripts/run_paper_phase1.py

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

# Project root on path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dine_trade.agents.analyst.gemini_analyst import get_conviction_score
from dine_trade.config.logging_config import setup_logging
from dine_trade.config.settings import UNIVERSE_DEFAULT
from dine_trade.data.connectors.alpaca_connector import (
    get_latest_price_from_bars,
    get_latest_quote_mid,
)
from dine_trade.data.providers import get_ohlcv_with_failover
from dine_trade.data.feeds.news_feed import get_recent_headlines
from dine_trade.execution.alpaca_client import smart_limit_order
from dine_trade.risk.limits import price_vs_ma_allowed
from dine_trade.utils.data_validator import validate_price_agreement

# Fixed small qty for Phase 1 paper
PHASE1_QTY = 1
CONVICTION_THRESHOLD = 8.0
MA_WINDOW = 20
PRICE_VS_MA_DEVIATION_PCT = 5.0
DATA_VALIDATOR_TOLERANCE_PCT = 0.1


def _ensure_log_dir():
    log_dir = os.path.join(_ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def _setup_logging():
    # Use shared logging configuration; keep this helper for backwards compatibility
    # with the existing script structure.
    return setup_logging("dine_trade.phase1", log_file_prefix="phase1")


def main() -> int:
    logger = _setup_logging()
    symbol = (UNIVERSE_DEFAULT or ["NVDA"])[0]

    logger.info("Phase 1 paper run started for %s", symbol)

    # 1) Fetch OHLCV and headlines
    ohlcv_df = get_ohlcv_with_failover(symbol, days=100)
    if ohlcv_df.empty:
        logger.error("No OHLCV data for %s; aborting", symbol)
        return 1
    logger.info("OHLCV rows: %d", len(ohlcv_df))

    headlines = get_recent_headlines(symbol, limit=10)
    logger.info("Headlines fetched: %d", len(headlines))

    # 2) 20-day MA and price_vs_ma_allowed
    close_col = "close" if "close" in ohlcv_df.columns else ohlcv_df.columns[-1]
    closes = ohlcv_df[close_col].astype(float)
    ma20 = closes.rolling(MA_WINDOW, min_periods=1).mean().iloc[-1]
    latest_close = float(closes.iloc[-1])
    ma_ok = price_vs_ma_allowed(latest_close, ma20, max_deviation_pct=PRICE_VS_MA_DEVIATION_PCT)
    logger.info("MA20=%.2f, latest_close=%.2f, price_vs_ma_allowed=%s", ma20, latest_close, ma_ok)

    # 3) Gemini get_conviction_score
    score, reasoning = get_conviction_score(ohlcv_df, headlines, symbol)
    logger.info("Conviction score=%.1f, reasoning=%s", score, reasoning[:200] if reasoning else "")

    # 4) Before any order: OHLCV-based price and Alpaca quote mid; DataValidator
    price_from_bars = get_latest_price_from_bars(symbol)
    _, _, quote_mid = get_latest_quote_mid(symbol)
    price_from_quote = quote_mid

    if price_from_bars is None:
        logger.error("No price from bars; aborting order")
        return 1
    if price_from_quote is None:
        logger.error("No quote mid; aborting order")
        return 1

    valid, msg = validate_price_agreement(
        price_from_bars, price_from_quote, tolerance_pct=DATA_VALIDATOR_TOLERANCE_PCT
    )
    if not valid:
        logger.warning("DataValidator failed: %s; aborting order", msg)
        return 0  # not a crash, just no trade

    logger.info("DataValidator passed: %s", msg)

    # 5) If score > 8 and MA and DataValidator pass: smart_limit_order
    if score <= CONVICTION_THRESHOLD:
        logger.info("Score %.1f <= %s; not submitting order", score, CONVICTION_THRESHOLD)
        return 0
    if not ma_ok:
        logger.info("MA constraint not satisfied; not submitting order")
        return 0

    result = smart_limit_order(symbol, "buy", PHASE1_QTY, 60)
    if result.get("ok"):
        logger.info("Order submitted: %s", result.get("order_id") or result)
    else:
        logger.error("Order failed: %s", result.get("error", result))

    return 0


if __name__ == "__main__":
    sys.exit(main())
