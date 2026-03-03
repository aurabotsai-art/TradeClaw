"""Storage — Supabase (trade_log, daily_state, agent_runs, post_mortem), Redis."""

from dine_trade.storage.trade_logger import log_trade_attempt

__all__ = ["log_trade_attempt"]
