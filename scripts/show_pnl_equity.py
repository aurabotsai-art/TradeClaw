"""
Simple real-time PnL and equity curve viewer (CLI).

Reads:
  - historical daily_state rows from Supabase (equity_at_open, circuit_breaker_fired)
  - current account equity from Alpaca

Outputs:
  - table of equity_at_open over time (equity curve approximation)
  - today's equity_at_open vs current equity
  - daily PnL and daily drawdown percentage

Run from project root:
    python scripts/show_pnl_equity.py
"""

from __future__ import annotations

import os
import sys
from datetime import date
from typing import Any, Dict, List


def _ensure_root_on_path() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(script_dir)
    if root not in sys.path:
        sys.path.insert(0, root)
    return root


_ROOT = _ensure_root_on_path()

from dine_trade.execution.alpaca_client import get_account  # noqa: E402
from dine_trade.storage.supabase_client import _get_client  # noqa: E402


def _fetch_daily_state() -> List[Dict[str, Any]]:
    client = _get_client()
    res = (
        client.table("daily_state")
        .select("*")
        .order("date", desc=False)
        .execute()
    )
    data = getattr(res, "data", None)
    return data or []


def main() -> int:
    print("[show_pnl_equity] Fetching daily_state from Supabase...")
    try:
        rows = _fetch_daily_state()
    except RuntimeError as e:
        print(f"  ERROR: Supabase not configured: {e}")
        return 1

    if not rows:
        print("  No rows in daily_state table yet.")
    else:
        print("\nEquity curve (equity_at_open):")
        print("  Date        | Equity at open      | Circuit breaker fired")
        print("  ------------+---------------------+----------------------")
        for r in rows:
            d = r.get("date")
            eq_open = r.get("equity_at_open")
            cb = r.get("circuit_breaker_fired")
            print(
                f"  {d:<10} | {eq_open:>19,.2f} | {str(cb):<6}"
                if eq_open is not None
                else f"  {d:<10} | {'N/A':>19} | {str(cb):<6}"
            )

    # Today's daily PnL
    today = date.today().isoformat()
    today_row = next((r for r in rows if r.get("date") == today), None)

    print("\n[show_pnl_equity] Fetching current Alpaca account equity...")
    try:
        account = get_account()
    except Exception as e:  # pragma: no cover - network/API
        print(f"  ERROR: Failed to fetch Alpaca account: {e}")
        return 1

    try:
        current_equity = float(getattr(account, "equity"))
    except Exception:
        try:
            current_equity = float(account["equity"])  # type: ignore[index]
        except Exception:
            print("  ERROR: Could not parse equity from Alpaca account object.")
            return 1

    print(f"  Current account equity: {current_equity:,.2f}")

    if today_row is None:
        print(f"  No daily_state row for today ({today}); daily PnL unavailable.")
        return 0

    eq_open = today_row.get("equity_at_open")
    if eq_open is None:
        print("  Today's equity_at_open is NULL; daily PnL unavailable.")
        return 0

    try:
        eq_open_f = float(eq_open)
    except (TypeError, ValueError):
        print("  Could not interpret equity_at_open as float; daily PnL unavailable.")
        return 0

    daily_pnl = current_equity - eq_open_f
    daily_pnl_pct = (daily_pnl / eq_open_f * 100.0) if eq_open_f > 0 else 0.0
    daily_dd_pct = max(0.0, (eq_open_f - current_equity) / eq_open_f * 100.0)

    print(f"\nToday's equity_at_open: {eq_open_f:,.2f}")
    print(f"Daily PnL:             {daily_pnl:,.2f} ({daily_pnl_pct:.4f}%)")
    print(f"Daily drawdown:        {daily_dd_pct:.4f}%")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

