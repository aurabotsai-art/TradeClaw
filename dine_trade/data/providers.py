"""Data provider abstraction with optional failover between Alpaca and Polygon.

Primary:
  - Alpaca (via dine_trade.data.connectors.alpaca_connector)

Secondary (optional):
  - Polygon.io (via dine_trade.data.connectors.polygon_connector)

These helpers are used by higher-level scripts (e.g. run_paper_phase1,
run_consensus_trade) so that if Alpaca data endpoints are temporarily
unavailable or rate-limited, we can fall back to Polygon when configured.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from dine_trade.data.connectors import alpaca_connector
from dine_trade.data.connectors import polygon_connector
from dine_trade.config.settings import POLYGON_API_KEY

logger = logging.getLogger(__name__)


def get_ohlcv_with_failover(symbol: str, days: int = 100) -> pd.DataFrame:
    """Fetch OHLCV, trying Alpaca first, then Polygon if available."""
    # Try Alpaca
    try:
        df = alpaca_connector.get_ohlcv(symbol, days=days)
        if df is not None and not getattr(df, "empty", True):
            return df
        logger.warning("Alpaca OHLCV returned empty DataFrame for %s; trying Polygon.", symbol)
    except Exception as e:  # pragma: no cover - network/remote errors
        logger.warning("Alpaca OHLCV failed for %s: %s; trying Polygon.", symbol, e)

    # Fallback to Polygon if configured
    if POLYGON_API_KEY:
        try:
            df_poly = polygon_connector.get_ohlcv(symbol, days=days)
            if df_poly is not None and not getattr(df_poly, "empty", True):
                logger.info("Using Polygon OHLCV for %s as fallback.", symbol)
                return df_poly
        except Exception as e:  # pragma: no cover
            logger.warning("Polygon OHLCV failed for %s: %s", symbol, e)

    # If all fail, return empty DataFrame
    logger.error("All OHLCV data sources failed for %s; returning empty DataFrame.", symbol)
    return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])


def get_latest_price_with_failover(symbol: str) -> Optional[float]:
    """Fetch latest price, trying Alpaca first, then Polygon if configured."""
    # Primary: Alpaca (mid from quotes/bars)
    try:
        price = alpaca_connector.get_latest_price(symbol)
        if price is not None:
            return float(price)
        logger.warning("Alpaca latest price returned None for %s; trying Polygon.", symbol)
    except Exception as e:  # pragma: no cover
        logger.warning("Alpaca latest price failed for %s: %s; trying Polygon.", symbol, e)

    if POLYGON_API_KEY:
        try:
            price_poly = polygon_connector.get_latest_price(symbol)
            if price_poly is not None:
                logger.info("Using Polygon latest price for %s as fallback.", symbol)
                return float(price_poly)
        except Exception as e:  # pragma: no cover
            logger.warning("Polygon latest price failed for %s: %s", symbol, e)

    logger.error("All price data sources failed for %s; returning None.", symbol)
    return None

