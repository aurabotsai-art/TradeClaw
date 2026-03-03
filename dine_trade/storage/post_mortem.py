"""Post-mortem logging to Supabase when daily drawdown circuit breaker fires."""

from __future__ import annotations

from typing import Dict, Any

from dine_trade.storage.supabase_client import insert_post_mortem


def write_post_mortem(failure_state: Dict[str, Any]) -> None:
    """Persist failure_state into the Supabase `post_mortem` table.

    Expected failure_state keys:
      - triggered_at: ISO timestamp string
      - equity_at_open: float
      - current_equity: float
      - drawdown_pct: float
      - positions_snapshot: dict
      - sentiment_snapshot: dict
      - charts_snapshot: dict
      - agent_summary: dict (optional)
    """
    insert_post_mortem(failure_state)

