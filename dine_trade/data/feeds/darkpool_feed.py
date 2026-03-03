"""Dark pool and whale flow monitoring.

Phase 10.1:
    - get_dark_pool_prints(symbol, lookback_hours=24) -> list[dict]
    - detect_whale_accumulation(prints: list) -> dict

Data sources (pluggable):
    - Unusual Whales API or Quiver Quant API (large off-exchange prints).
    - FMP get_dark_pool_levels(symbol) for major dark pool price clusters.

This module provides a thin abstraction so the upstream Researcher Agent can
consume dark-pool context without caring which vendor is used underneath.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import requests

from dine_trade.config.settings import FMP_API_KEY
from dine_trade.storage.supabase_client import insert_whale_print

logger = logging.getLogger(__name__)

# Optional third-party APIs
UNUSUAL_WHALES_API_KEY = os.getenv("UNUSUAL_WHALES_API_KEY", "").strip()
QUIVER_API_KEY = os.getenv("QUIVER_API_KEY", "").strip()


def _iso_now_minus(hours: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    return dt.isoformat()


def _from_unusual_whales(symbol: str, lookback_hours: int) -> List[Dict[str, Any]]:
    """Fetch dark pool / large off-exchange prints from Unusual Whales, if configured.

    This is a placeholder; the exact endpoint and schema depend on the Unusual Whales API.
    If UNUSUAL_WHALES_API_KEY is not set or the call fails, returns [].
    """
    if not UNUSUAL_WHALES_API_KEY:
        return []
    try:
        # NOTE: URL and params are illustrative; adjust to match vendor docs.
        url = "https://api.unusualwhales.com/darkpool/prints"
        params = {
            "symbol": symbol,
            "since": _iso_now_minus(lookback_hours),
            "min_shares": 10_000,
        }
        headers = {"Authorization": f"Bearer {UNUSUAL_WHALES_API_KEY}"}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:  # pragma: no cover - external API
        logger.warning("Unusual Whales darkpool fetch failed for %s: %s", symbol, e)
        return []

    prints: List[Dict[str, Any]] = []
    for item in data or []:
        try:
            price = float(item.get("price"))
            vol = float(item.get("shares"))
        except (TypeError, ValueError):
            continue
        ts = item.get("timestamp") or item.get("time")
        venue = item.get("venue") or "UNUSUAL_WHALES"
        above_ask = bool(item.get("above_ask"))
        prints.append(
            {
                "symbol": symbol,
                "price": price,
                "volume": vol,
                "timestamp": ts,
                "venue": venue,
                "above_ask": above_ask,
                "source": "UNUSUAL_WHALES",
            }
        )
    return prints


def _from_quiver(symbol: str, lookback_hours: int) -> List[Dict[str, Any]]:
    """Fetch dark pool prints from Quiver Quant, if configured.

    Placeholder; if QUIVER_API_KEY is not set or call fails, returns [].
    """
    if not QUIVER_API_KEY:
        return []
    try:
        # NOTE: URL schematic; adjust to actual Quiver Quant API.
        url = f"https://api.quiverquant.com/beta/darkpools/{symbol}"
        headers = {"Authorization": f"Token {QUIVER_API_KEY}"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:  # pragma: no cover
        logger.warning("Quiver darkpool fetch failed for %s: %s", symbol, e)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    prints: List[Dict[str, Any]] = []
    for item in data or []:
        try:
            ts_raw = item.get("Date") or item.get("timestamp")
            ts = datetime.fromisoformat(ts_raw)
        except Exception:
            continue
        if ts < cutoff:
            continue
        try:
            price = float(item.get("Price"))
            vol = float(item.get("Shares"))
        except (TypeError, ValueError):
            continue
        venue = item.get("Venue") or "QUIVER"
        above_ask = bool(item.get("AboveAsk"))
        prints.append(
            {
                "symbol": symbol,
                "price": price,
                "volume": vol,
                "timestamp": ts.isoformat(),
                "venue": venue,
                "above_ask": above_ask,
                "source": "QUIVER",
            }
        )
    return prints


def _from_fmp_levels(symbol: str) -> List[Dict[str, Any]]:
    """Fetch major dark-pool levels from FMP, if FMP_API_KEY configured.

    This is not tick-level prints, but price clusters; we normalize them into a
    similar shape so they can be stored and surfaced to the Researcher.
    """
    if not FMP_API_KEY:
        return []
    url = f"https://financialmodelingprep.com/api/v4/dark_pool/{symbol}"
    params = {"apikey": FMP_API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:  # pragma: no cover
        logger.warning("FMP dark pool levels fetch failed for %s: %s", symbol, e)
        return []

    prints: List[Dict[str, Any]] = []
    for item in data or []:
        try:
            price = float(item.get("price"))
            vol = float(item.get("volume"))
        except (TypeError, ValueError):
            continue
        ts = item.get("date") or datetime.now(timezone.utc).isoformat()
        prints.append(
            {
                "symbol": symbol,
                "price": price,
                "volume": vol,
                "timestamp": ts,
                "venue": item.get("venue") or "FMP",
                "above_ask": bool(item.get("aboveAsk", False)),
                "source": "FMP",
            }
        )
    return prints


def get_dark_pool_prints(symbol: str, lookback_hours: int = 24, min_shares: int = 10_000) -> List[Dict[str, Any]]:
    """Aggregate dark-pool / whale prints from configured sources.

    Returns list of dicts with fields:
        - symbol
        - price
        - volume
        - timestamp (ISO string)
        - venue
        - above_ask (bool)
        - source
    """
    symbol = symbol.upper()

    prints: List[Dict[str, Any]] = []
    prints.extend(_from_unusual_whales(symbol, lookback_hours))
    prints.extend(_from_quiver(symbol, lookback_hours))
    prints.extend(_from_fmp_levels(symbol))

    # Filter by volume threshold and sort by timestamp descending
    filtered: List[Dict[str, Any]] = []
    for p in prints:
        try:
            vol = float(p.get("volume", 0.0))
        except (TypeError, ValueError):
            continue
        if vol < float(min_shares):
            continue
        filtered.append(p)

    # Store whale prints in Supabase
    for p in filtered:
        try:
            insert_whale_print(p)
        except RuntimeError:
            # Supabase not configured; skip remote storage.
            logger.warning("Supabase not configured; skipping whale_print insert.")
            break

    # Sort newest first
    def _ts_key(x: Dict[str, Any]) -> Any:
        return x.get("timestamp") or ""

    filtered.sort(key=_ts_key, reverse=True)
    return filtered


def detect_whale_accumulation(prints: List[Dict[str, Any]], price_tolerance_pct: float = 1.0) -> Dict[str, Any]:
    """Cluster prints by price level and detect accumulation.

    Logic:
        - Group prints whose prices are within `price_tolerance_pct` of each other.
        - If any cluster has >3 large prints (|prints| > 3) → ACCUMULATION.
    """
    if not prints:
        return {"signal": "NONE", "clusters": []}

    # Simple clustering by iterating prints sorted by price.
    sorted_prints = sorted(prints, key=lambda p: float(p.get("price", 0.0)))
    clusters: List[List[Dict[str, Any]]] = []
    current_cluster: List[Dict[str, Any]] = []

    for p in sorted_prints:
        price = float(p.get("price", 0.0))
        if not current_cluster:
            current_cluster.append(p)
            continue
        ref_price = float(current_cluster[0].get("price", 0.0))
        if ref_price <= 0:
            current_cluster.append(p)
            continue
        deviation_pct = abs(price - ref_price) / ref_price * 100.0
        if deviation_pct <= price_tolerance_pct:
            current_cluster.append(p)
        else:
            clusters.append(current_cluster)
            current_cluster = [p]
    if current_cluster:
        clusters.append(current_cluster)

    best_cluster: List[Dict[str, Any]] | None = None
    for cluster in clusters:
        if len(cluster) > 3:
            best_cluster = cluster
            break

    if best_cluster is None:
        return {"signal": "NONE", "clusters": clusters}

    # Summarize the strongest accumulation cluster
    prices = [float(p.get("price", 0.0)) for p in best_cluster]
    vols = [float(p.get("volume", 0.0)) for p in best_cluster]
    avg_price = sum(prices) / len(prices) if prices else 0.0
    total_vol = sum(vols)

    return {
        "signal": "ACCUMULATION",
        "cluster_size": len(best_cluster),
        "avg_price": avg_price,
        "total_volume": total_vol,
        "clusters": clusters,
    }

