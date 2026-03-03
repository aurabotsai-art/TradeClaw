"""Macro Monitor Agent.

Tracks macro events and regimes that can move all markets simultaneously.

Functions:
- get_upcoming_events(days_ahead=7) -> list[dict]
    - Combines FMP economic calendar and (optionally) earnings dates for
      symbols in UNIVERSE_DEFAULT.
    - Tags events with volatility_impact: "LOW" | "MEDIUM" | "HIGH" | "EXTREME".

- assess_macro_regime() -> dict
    - Uses FRED time series (if FRED_API_KEY configured) to classify:
        * rate_env: "RISING" | "FALLING" | "FLAT"
        * inflation_regime: "RISING" | "FALLING" | "STABLE"
        * employment_trend: "IMPROVING" | "DETERIORATING" | "STABLE"
        * risk_off: bool

Output of these functions can be fed into other agents as context headers.
"""

from __future__ import annotations

import datetime as _dt
import logging
import os
from typing import Any, Dict, List

import requests

from dine_trade.config.settings import FMP_API_KEY, UNIVERSE_DEFAULT

logger = logging.getLogger(__name__)

FRED_API_KEY = os.getenv("FRED_API_KEY", "").strip()


def _today_utc() -> _dt.date:
    return _dt.datetime.utcnow().date()


def _fmt_date(d: _dt.date) -> str:
    return d.strftime("%Y-%m-%d")


def _vol_impact_for_event_name(name: str) -> str:
    n = name.lower()
    if "fomc" in n or "federal funds rate" in n or "fed interest rate" in n:
        return "EXTREME"
    if "cpi" in n or "inflation" in n:
        return "HIGH"
    if "non-farm" in n or "nonfarm" in n or "payroll" in n or "nfp" in n or "unemployment" in n:
        return "HIGH"
    if "gdp" in n or "pmi" in n or "ism" in n:
        return "MEDIUM"
    return "LOW"


def _fetch_fmp_economic_calendar(start: str, end: str) -> List[Dict[str, Any]]:
    if not FMP_API_KEY:
        return []
    url = "https://financialmodelingprep.com/api/v3/economic_calendar"
    params = {"from": start, "to": end, "apikey": FMP_API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
    except Exception as e:  # pragma: no cover
        logger.warning("FMP economic_calendar fetch failed: %s", e)
    return []


def _fetch_fmp_earnings_calendar(start: str, end: str, symbol: str) -> List[Dict[str, Any]]:
    if not FMP_API_KEY:
        return []
    url = "https://financialmodelingprep.com/api/v3/earning_calendar"
    params = {"from": start, "to": end, "symbol": symbol, "apikey": FMP_API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
    except Exception as e:  # pragma: no cover
        logger.warning("FMP earning_calendar fetch failed for %s: %s", symbol, e)
    return []


def get_upcoming_events(days_ahead: int = 7) -> List[Dict[str, Any]]:
    """Return upcoming macro and earnings events in the next days_ahead days.

    Each event dict includes:
      {
        "date": "YYYY-MM-DD",
        "type": "FOMC" | "CPI" | "NFP" | "EARNINGS" | "OTHER",
        "name": str,
        "symbol": str | None,
        "volatility_impact": "LOW" | "MEDIUM" | "HIGH" | "EXTREME",
        "raw": <original event dict>,
      }
    """
    today = _today_utc()
    end_date = today + _dt.timedelta(days=max(days_ahead, 1))
    start_str = _fmt_date(today)
    end_str = _fmt_date(end_date)

    events: List[Dict[str, Any]] = []

    # Economic calendar (macro)
    econ = _fetch_fmp_economic_calendar(start_str, end_str)
    for e in econ:
        name = str(e.get("event") or e.get("name") or "").strip()
        if not name:
            continue
        date_str = str(e.get("date") or e.get("dateTime") or e.get("date_time") or "")
        event_type = "OTHER"
        n_lower = name.lower()
        if "fomc" in n_lower or "fed interest rate" in n_lower or "federal funds" in n_lower:
            event_type = "FOMC"
        elif "cpi" in n_lower or "consumer price" in n_lower or "inflation" in n_lower:
            event_type = "CPI"
        elif "non-farm" in n_lower or "nonfarm" in n_lower or "payroll" in n_lower or "nfp" in n_lower:
            event_type = "NFP"

        vol = _vol_impact_for_event_name(name)
        events.append(
            {
                "date": date_str[:10],
                "type": event_type,
                "name": name,
                "symbol": None,
                "volatility_impact": vol,
                "raw": e,
            }
        )

    # Earnings dates for universe symbols
    for sym in UNIVERSE_DEFAULT:
        ec = _fetch_fmp_earnings_calendar(start_str, end_str, sym)
        for row in ec:
            date_str = str(row.get("date") or row.get("dateTime") or "")
            name = f"Earnings for {sym}"
            events.append(
                {
                    "date": date_str[:10],
                    "type": "EARNINGS",
                    "name": name,
                    "symbol": sym,
                    "volatility_impact": "MEDIUM",
                    "raw": row,
                }
            )

    return events


def _fred_series_observations(series_id: str, limit: int = 12) -> List[Dict[str, Any]]:
    """Fetch recent observations for a FRED series."""
    if not FRED_API_KEY:
        return []
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    }
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        obs = data.get("observations", [])
        return obs
    except Exception as e:  # pragma: no cover
        logger.warning("FRED fetch failed for %s: %s", series_id, e)
        return []


def _trend_from_observations(obs: List[Dict[str, Any]]) -> str:
    """Classify simple trend from FRED observations: RISING/FALLING/FLAT."""
    if len(obs) < 3:
        return "UNSPECIFIED"
    # Observations are sorted desc by date
    try:
        vals = [float(o["value"]) for o in obs if o.get("value") not in ("", ".")]
    except (TypeError, ValueError):
        return "UNSPECIFIED"
    if len(vals) < 3:
        return "UNSPECIFIED"

    recent = vals[0]
    older = vals[-1]
    diff = recent - older
    # Simple thresholding; units depend on series, keep small
    if diff > 0.1:
        return "RISING"
    if diff < -0.1:
        return "FALLING"
    return "FLAT"


def assess_macro_regime() -> Dict[str, Any]:
    """Assess high-level macro regime using FRED time series.

    Returns:
      {
        "rate_env": "RISING"|"FALLING"|"FLAT"|"UNSPECIFIED",
        "inflation_regime": "RISING"|"FALLING"|"STABLE"|"UNSPECIFIED",
        "employment_trend": "IMPROVING"|"DETERIORATING"|"STABLE"|"UNSPECIFIED",
        "risk_off": bool,
      }
    """
    if not FRED_API_KEY:
        return {
            "rate_env": "UNSPECIFIED",
            "inflation_regime": "UNSPECIFIED",
            "employment_trend": "UNSPECIFIED",
            "risk_off": False,
        }

    # FEDFUNDS: Fed Funds Rate (interest-rate environment)
    fed_obs = _fred_series_observations("FEDFUNDS", limit=12)
    rate_trend = _trend_from_observations(fed_obs)

    # CPIAUCSL: CPI for All Urban Consumers
    cpi_obs = _fred_series_observations("CPIAUCSL", limit=12)
    cpi_trend = _trend_from_observations(cpi_obs)
    if cpi_trend == "RISING":
        inflation_regime = "RISING"
    elif cpi_trend == "FALLING":
        inflation_regime = "FALLING"
    elif cpi_trend == "FLAT":
        inflation_regime = "STABLE"
    else:
        inflation_regime = "UNSPECIFIED"

    # UNRATE: Unemployment Rate
    unrate_obs = _fred_series_observations("UNRATE", limit=12)
    unrate_trend = _trend_from_observations(unrate_obs)
    if unrate_trend == "RISING":
        employment_trend = "DETERIORATING"
    elif unrate_trend == "FALLING":
        employment_trend = "IMPROVING"
    elif unrate_trend == "FLAT":
        employment_trend = "STABLE"
    else:
        employment_trend = "UNSPECIFIED"

    # Simple risk-off heuristic:
    # - Rate_env RISING and inflation RISING or
    # - Employment DETERIORATING
    risk_off = False
    if rate_trend == "RISING" and inflation_regime == "RISING":
        risk_off = True
    if employment_trend == "DETERIORATING":
        risk_off = True

    return {
        "rate_env": rate_trend,
        "inflation_regime": inflation_regime,
        "employment_trend": employment_trend,
        "risk_off": risk_off,
    }

