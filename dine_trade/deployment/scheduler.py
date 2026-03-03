"""Market hours scheduler utilities using APScheduler.

Phase 12.1:
    - is_market_open(asset_class: str) -> bool
    - get_next_market_open(asset_class: str) -> datetime

Asset classes:
    - EQUITY: Mon–Fri 9:30–16:00 America/New_York, excluding a small NYSE holiday set.
    - CRYPTO: always True.
    - FOREX: Sun 17:00–Fri 17:00 America/New_York (approximate, excluding major holidays).

Also defines:
    PRE_MARKET_TASKS
    MARKET_OPEN_TASKS
    MARKET_CLOSE_TASKS
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import List

from zoneinfo import ZoneInfo

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
except ImportError:  # pragma: no cover - optional dependency
    AsyncIOScheduler = None  # type: ignore[assignment]


NY_TZ = ZoneInfo("America/New_York")

PRE_MARKET_TASKS: List[str] = [
    "load_daily_state",
    "fetch_macro_events",
    "reset_drawdown_counter",
]

MARKET_OPEN_TASKS: List[str] = [
    "start_ws_streams",
    "enable_trading",
    "run_consensus_loop",
]

MARKET_CLOSE_TASKS: List[str] = [
    "generate_daily_report",
    "close_intraday_positions",
    "backup_to_supabase",
]


def _today_ny() -> datetime:
    return datetime.now(tz=NY_TZ)


def _is_nyse_holiday(d: datetime) -> bool:
    """Minimal NYSE holiday approximation (fixed dates only).

    For full accuracy, integrate an exchange calendar library; here we
    include only the most common fixed-date closures.
    """
    y = d.year
    # New Year's Day
    new_years = datetime(y, 1, 1, tzinfo=NY_TZ)
    # Independence Day
    july4 = datetime(y, 7, 4, tzinfo=NY_TZ)
    # Christmas
    xmas = datetime(y, 12, 25, tzinfo=NY_TZ)
    holidays = {new_years.date(), july4.date(), xmas.date()}
    return d.date() in holidays


def is_market_open(asset_class: str) -> bool:
    """Return True if the market for the given asset_class is currently open."""
    ac = asset_class.upper()
    now_utc = datetime.now(timezone.utc)
    now_ny = now_utc.astimezone(NY_TZ)

    if ac == "CRYPTO":
        return True

    if ac == "EQUITY":
        if now_ny.weekday() >= 5:  # Sat/Sun
            return False
        if _is_nyse_holiday(now_ny):
            return False
        open_t = time(9, 30)
        close_t = time(16, 0)
        return open_t <= now_ny.time() <= close_t

    if ac == "FOREX":
        # Approximate: Sun 17:00 through Fri 17:00 NY time.
        wd = now_ny.weekday()
        if wd == 6:  # Sunday
            return now_ny.time() >= time(17, 0)
        if wd == 5:  # Saturday
            return False
        if wd == 4:  # Friday
            return now_ny.time() <= time(17, 0)
        # Mon–Thu
        return True

    # Unknown asset class; default to False.
    return False


def get_next_market_open(asset_class: str) -> datetime:
    """Return the next market open datetime in NY time for the given asset_class."""
    ac = asset_class.upper()
    now_ny = _today_ny()

    if ac == "CRYPTO":
        # Always open; return now.
        return now_ny

    if ac == "EQUITY":
        # Start from today and move forward up to 10 days to find next non-weekend, non-holiday business day.
        for delta in range(0, 10):
            candidate = now_ny + timedelta(days=delta)
            if candidate.weekday() >= 5 or _is_nyse_holiday(candidate):
                continue
            open_dt = datetime(
                candidate.year,
                candidate.month,
                candidate.day,
                9,
                30,
                tzinfo=NY_TZ,
            )
            if open_dt > now_ny:
                return open_dt
        return now_ny

    if ac == "FOREX":
        # Find next Sunday 17:00 or same-week Mon–Fri windows.
        wd = now_ny.weekday()
        current_time = now_ny.time()
        if wd == 6 and current_time < time(17, 0):
            # Today is Sunday before open.
            return datetime(now_ny.year, now_ny.month, now_ny.day, 17, 0, tzinfo=NY_TZ)
        if wd == 5:
            # Saturday -> next Sunday 17:00
            next_sun = now_ny + timedelta(days=(6 - wd))
            return datetime(next_sun.year, next_sun.month, next_sun.day, 17, 0, tzinfo=NY_TZ)
        if wd == 4 and current_time > time(17, 0):
            # Friday after close -> next Sunday 17:00
            days_to_sun = (6 - wd) % 7
            next_sun = now_ny + timedelta(days=days_to_sun)
            return datetime(next_sun.year, next_sun.month, next_sun.day, 17, 0, tzinfo=NY_TZ)
        # Otherwise already in an open window; return now.
        return now_ny

    return now_ny


def create_scheduler() -> "AsyncIOScheduler | None":  # type: ignore[name-defined]
    """Create and return an AsyncIOScheduler, or None if APScheduler is missing."""
    if AsyncIOScheduler is None:
        return None
    return AsyncIOScheduler()

