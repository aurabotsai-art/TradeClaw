"""Supabase: trade_log, daily_state, agent_runs, post_mortem."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict

from supabase import Client, create_client

from dine_trade.config.settings import SUPABASE_KEY, SUPABASE_URL


def _get_client() -> Client:
    """Create and return a Supabase client using configured URL/key.

    NOTE: This should only be used on the backend with a service role key,
    never exposed to client-side code.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase URL or key not configured.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------------------------------------------------------
# trade_log helpers
# ---------------------------------------------------------------------------

def insert_trade_log(row: Dict[str, Any]) -> None:
    """Insert a row into the trade_log table.

    Expected keys (match Supabase schema):
      - symbol: text
      - side: text ('buy' / 'sell')
      - qty: numeric
      - price: numeric (execution or limit price), optional
      - order_id: text (optional, internal id)
      - alpaca_order_id: text (optional, Alpaca id)
      - consensus_snapshot: json/dict (optional)
      - strategy_phase: text (e.g. 'phase1', 'phase3', 'live')

    created_at is set by the database default.
    """
    client = _get_client()
    client.table("trade_log").insert(row).execute()


# ---------------------------------------------------------------------------
# slippage_log helpers
# ---------------------------------------------------------------------------

def insert_slippage_log(row: Dict[str, Any]) -> None:
    """Insert a row into the slippage_log table.

    Recommended keys:
      - order_id: text
      - symbol: text
      - side: text ('buy' / 'sell')
      - expected_price: numeric
      - fill_price: numeric
      - slippage: numeric  (fill_price - expected_price; negative = better)
      - asset_class: text ('EQUITY' | 'CRYPTO' | 'FOREX')
      - venue: text (e.g. 'ALPACA', 'BINANCE_SPOT', 'OANDA')
    """
    client = _get_client()
    client.table("slippage_log").insert(row).execute()


# ---------------------------------------------------------------------------
# daily_state helpers
# ---------------------------------------------------------------------------

def upsert_daily_state(
    trading_date: date,
    equity_at_open: float,
    circuit_breaker_fired: bool,
) -> None:
    """Upsert the daily_state row for a given trading date.

    If a row for `trading_date` already exists, it is updated; otherwise it is
    created. The `updated_at` column is refreshed on each call.
    """
    client = _get_client()
    row = {
        "date": trading_date.isoformat(),
        "equity_at_open": float(equity_at_open),
        "circuit_breaker_fired": bool(circuit_breaker_fired),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    client.table("daily_state").upsert(row, on_conflict="date").execute()


# ---------------------------------------------------------------------------
# agent_runs helpers
# ---------------------------------------------------------------------------

def insert_agent_run(
    run_id: str,
    agent_name: str,
    symbol: str,
    verdict: str,
    score: float | None,
    reasoning: str,
) -> None:
    """Insert a single agent_runs row.

    - run_id: correlation id for a full consensus + execution run.
    - agent_name: 'researcher', 'sentiment', 'chartist', 'risk_officer', etc.
    """
    client = _get_client()
    row = {
        "run_id": run_id,
        "agent_name": agent_name,
        "symbol": symbol,
        "verdict": verdict,
        "score": score,
        "reasoning": reasoning,
    }
    client.table("agent_runs").insert(row).execute()


# ---------------------------------------------------------------------------
# post_mortem helpers
# ---------------------------------------------------------------------------

def insert_post_mortem(failure_state: Dict[str, Any]) -> None:
    """Insert a post_mortem row.

    The `post_mortem` table (Phase 4.1) should have columns:
      - triggered_at (timestamptz)
      - equity_at_open (numeric)
      - current_equity (numeric)
      - drawdown_pct (numeric)
      - positions_snapshot (jsonb)
      - sentiment_snapshot (jsonb)
      - charts_snapshot (jsonb)
      - agent_summary (jsonb)
      - created_at (timestamptz, default now)
    """
    client = _get_client()
    client.table("post_mortem").insert(failure_state).execute()


# ---------------------------------------------------------------------------
# whale_prints helpers
# ---------------------------------------------------------------------------

def insert_whale_print(row: Dict[str, Any]) -> None:
    """Insert a single whale print into the whale_prints table.

    Recommended columns:
      - symbol: text
      - price: numeric
      - volume: numeric
      - timestamp: timestamptz
      - venue: text
      - above_ask: boolean
      - source: text (e.g. 'UNUSUAL_WHALES', 'QUIVER', 'FMP')
    """
    client = _get_client()
    client.table("whale_prints").insert(row).execute()


# ---------------------------------------------------------------------------
# trade_outcomes (evolution / performance tracker)
# ---------------------------------------------------------------------------

def insert_trade_outcome(row: Dict[str, Any]) -> None:
    """Insert a trade outcome row for performance tracking.

    Expected keys (trade_outcomes table):
      - symbol, side, asset_class, entry_time, exit_time
      - pnl, hold_duration_seconds, mfe, mae (max favorable/adverse excursion)
      - agent_verdicts (jsonb), market_regime, macro_snapshot (jsonb)
      - technical_snapshot (jsonb), sentiment_score
    """
    client = _get_client()
    client.table("trade_outcomes").insert(row).execute()


def select_trade_outcomes_since(lookback_days: int) -> list:
    """Return trade_outcomes rows with exit_time >= (now - lookback_days)."""
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()
    client = _get_client()
    r = client.table("trade_outcomes").select("*").gte("exit_time", since).execute()
    return list(r.data) if r.data else []


def select_trade_outcomes_between(start_iso: str, end_iso: str) -> list:
    """Return trade_outcomes rows with exit_time in [start_iso, end_iso]."""
    client = _get_client()
    r = (
        client.table("trade_outcomes")
        .select("*")
        .gte("exit_time", start_iso)
        .lte("exit_time", end_iso)
        .execute()
    )
    return list(r.data) if r.data else []


# ---------------------------------------------------------------------------
# strategy_performance (computed metrics)
# ---------------------------------------------------------------------------

def insert_strategy_performance(row: Dict[str, Any]) -> None:
    """Insert a strategy_performance row (computed metrics snapshot).

    Expected keys: lookback_days, computed_at, win_rate, avg_winner, avg_loser,
    sharpe, max_drawdown, by_regime (jsonb), by_asset_class (jsonb), by_agent (jsonb).
    """
    client = _get_client()
    client.table("strategy_performance").insert(row).execute()


# ---------------------------------------------------------------------------
# strategy_params (tuned hyperparameters)
# ---------------------------------------------------------------------------

def insert_strategy_params(row: Dict[str, Any]) -> None:
    """Insert a row into the strategy_params table.

    Recommended columns:
      - tuned_at: timestamptz
      - atr_mult: numeric
      - consensus_threshold: numeric
      - kelly_fraction_cap: numeric
      - twap_slices: integer
      - vwap_window_minutes: integer (optional)
      - baseline_sharpe: numeric
      - tuned_sharpe: numeric
      - improvement_pct: numeric
      - details: jsonb (optional, e.g. Optuna study summary)
    """
    client = _get_client()
    client.table("strategy_params").insert(row).execute()


def get_latest_strategy_params() -> Dict[str, Any] | None:
    """Return the most recent strategy_params row, or None if table is empty."""
    client = _get_client()
    res = (
        client.table("strategy_params")
        .select("*")
        .order("tuned_at", desc=True)
        .limit(1)
        .execute()
    )
    data = res.data or []
    return data[0] if data else None


def select_strategy_params_between(start_iso: str, end_iso: str) -> list:
    """Return strategy_params rows with tuned_at in [start_iso, end_iso]."""
    client = _get_client()
    r = (
        client.table("strategy_params")
        .select("*")
        .gte("tuned_at", start_iso)
        .lte("tuned_at", end_iso)
        .order("tuned_at", desc=False)
        .execute()
    )
    return list(r.data) if r.data else []


# ---------------------------------------------------------------------------
# universe_candidates (universe expansion agent)
# ---------------------------------------------------------------------------

def insert_universe_candidate(row: Dict[str, Any]) -> None:
    """Insert a candidate row into the universe_candidates table.

    Recommended columns:
      - symbol: text
      - asset_class: text ('EQUITY' | 'CRYPTO' | 'FOREX')
      - score: numeric
      - components: jsonb (breakdown of scores / reasons)
      - scanned_at: timestamptz
    """
    client = _get_client()
    client.table("universe_candidates").insert(row).execute()


def select_universe_candidates(limit: int = 100) -> list[Dict[str, Any]]:
    """Return most recent universe_candidates rows (default up to 100)."""
    client = _get_client()
    res = (
        client.table("universe_candidates")
        .select("*")
        .order("scanned_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(res.data or [])


def select_universe_candidates_between(start_iso: str, end_iso: str) -> list[Dict[str, Any]]:
    """Return universe_candidates rows with scanned_at in [start_iso, end_iso]."""
    client = _get_client()
    r = (
        client.table("universe_candidates")
        .select("*")
        .gte("scanned_at", start_iso)
        .lte("scanned_at", end_iso)
        .order("scanned_at", desc=True)
        .execute()
    )
    return list(r.data or [])


def upload_storage_file(
    bucket: str,
    path: str,
    file_bytes: bytes,
    *,
    content_type: str = "application/octet-stream",
    upsert: bool = True,
) -> str:
    """Upload bytes to Supabase storage bucket. Returns storage path (bucket/path)."""
    client = _get_client()
    opts: Dict[str, Any] = {"content-type": content_type}
    if upsert:
        opts["upsert"] = True
    client.storage.from_(bucket).upload(path, file_bytes, opts)
    return f"{bucket}/{path}"
