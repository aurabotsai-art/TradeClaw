"""Trade and state logging.

Logs every trade attempt (and its consensus context) to:
  - local log file (e.g. dine_trade/logs/)
  - Supabase `trade_log` table (Phase 4.1)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from dine_trade.storage.supabase_client import insert_trade_log

LOG_DIR = Path(__file__).resolve().parents[2] / "dine_trade" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_logger = logging.getLogger("dine_trade.trade_logger")
if not _logger.handlers:
    _logger.setLevel(logging.INFO)
    fh = logging.FileHandler(LOG_DIR / "trades.log")
    fh.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z"
    )
    fh.setFormatter(fmt)
    _logger.addHandler(fh)


def log_trade_attempt(
    symbol: str,
    side: str,
    qty: float,
    limit_price: Optional[float],
    consensus_snapshot: Dict[str, Any],
    strategy_phase: str = "live",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a trade attempt with consensus context."""
    row: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "qty": float(qty),
        # Store limit price under `price` to match trade_log schema
        "price": float(limit_price) if limit_price is not None else None,
        "consensus_snapshot": consensus_snapshot,
        "strategy_phase": strategy_phase,
    }
    if extra:
        row.update(extra)

    # File log (JSON line for easy parsing)
    _logger.info("trade_attempt %s", json.dumps(row, separators=(",", ":")))

    # Remote log (Supabase). If Supabase isn't configured, this will raise
    # RuntimeError; callers can decide whether to catch it or let it bubble.
    try:
        insert_trade_log(row)
    except RuntimeError:
        # Supabase not configured; skip remote logging.
        return

