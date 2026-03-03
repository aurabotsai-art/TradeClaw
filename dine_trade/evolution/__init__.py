"""Evolution: performance tracking, strategy metrics, agent weighting, auto-tuning, and feedback loop."""

from dine_trade.evolution.performance_tracker import (
    build_trade_outcome_row,
    compute_strategy_metrics,
    record_trade_outcome,
)
from dine_trade.evolution.strategy_mutator import (
    AGENT_WEIGHTS_DEFAULT,
    CONSENSUS_THRESHOLD,
    MIN_AGENT_WEIGHT,
    compute_agent_ics,
    get_agent_weights,
    is_approved_weighted,
    rebalance_agent_weights,
    rebalance_weights_from_supabase,
    weighted_consensus_score,
)
from dine_trade.evolution.auto_retrain import (
    TunableParams,
    auto_tune_weekly,
    optimize_parameters,
    run_walk_forward,
)
from dine_trade.evolution.feedback_loop import (
    get_feedback_weight,
    get_similar_trade_outcomes,
    record_trade_outcome_to_memory,
    record_trade_to_memory,
)
from dine_trade.evolution.monthly_review import (
    build_report_markdown,
    get_monthly_report_data,
    run_monthly_review,
)

__all__ = [
    "build_trade_outcome_row",
    "compute_strategy_metrics",
    "record_trade_outcome",
    "AGENT_WEIGHTS_DEFAULT",
    "CONSENSUS_THRESHOLD",
    "MIN_AGENT_WEIGHT",
    "compute_agent_ics",
    "get_agent_weights",
    "is_approved_weighted",
    "rebalance_agent_weights",
    "rebalance_weights_from_supabase",
    "weighted_consensus_score",
    "TunableParams",
    "auto_tune_weekly",
    "optimize_parameters",
    "run_walk_forward",
    "get_feedback_weight",
    "get_similar_trade_outcomes",
    "record_trade_outcome_to_memory",
    "record_trade_to_memory",
    "build_report_markdown",
    "get_monthly_report_data",
    "run_monthly_review",
]
