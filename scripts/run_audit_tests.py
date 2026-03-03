"""
Run Phase 5.6 audit tests:

- Yearly backtests (2008, 2020, 2022) with max DD and circuit-breaker behavior.
- Regime tests for 2022 Tech Bear and Aug 2024 Volatility.
- Walk-forward test.
- Monte Carlo analysis.

Results are printed to stdout and logged via the shared logging config.

Run from project root:
    python scripts/run_audit_tests.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Tuple


def _ensure_root_on_path() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(script_dir)
    if root not in sys.path:
        sys.path.insert(0, root)
    return root


_ROOT = _ensure_root_on_path()

import pandas as pd  # noqa: E402

from dine_trade.backtesting.engine import run_backtest  # noqa: E402
from dine_trade.backtesting.monte_carlo import monte_carlo_from_equity  # noqa: E402
from dine_trade.backtesting.regime_test import (  # noqa: E402
    RegimeTestResult,
    _breaches_daily_dd_limit,
    run_regime_tests,
)
from dine_trade.backtesting.signal_from_agents import generate_signals  # noqa: E402
from dine_trade.backtesting.walk_forward import walk_forward_test  # noqa: E402
from dine_trade.config.logging_config import setup_logging  # noqa: E402
from dine_trade.config.settings import (  # noqa: E402
    DAILY_DRAWDOWN_LIMIT_PCT,
    UNIVERSE_DEFAULT,
)
from dine_trade.data.connectors.alpaca_connector import get_ohlcv  # noqa: E402


logger = setup_logging("dine_trade.audit", log_file_prefix="audit")


def _slice_year(df: pd.DataFrame, year: int) -> pd.DataFrame:
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    mask = (df["date"] >= start) & (df["date"] <= end)
    return df.loc[mask].reset_index(drop=True)


def _run_yearly_backtest(
    symbol: str,
    df_full: pd.DataFrame,
    year: int,
    initial_equity: float,
    risk_pct: float,
    slippage_bps: float,
) -> None:
    df_year = _slice_year(df_full, year)
    if df_year.empty:
        logger.warning("No OHLCV data for %s in year %s; skipping.", symbol, year)
        print(f"[Year {year}] No data; skipped.")
        return

    signals = generate_signals(
        symbol,
        df_year,
        initial_equity=initial_equity,
        risk_per_trade_pct=risk_pct,
    )
    bt = run_backtest(df_year, signals, initial_equity=initial_equity, slippage_bps=slippage_bps)

    breached = _breaches_daily_dd_limit(bt.equity_curve, float(DAILY_DRAWDOWN_LIMIT_PCT))

    print(f"\n=== Year {year} Backtest ({symbol}) ===")
    print(f"Period:           {df_year['date'].iloc[0].date()} – {df_year['date'].iloc[-1].date()}")
    print(f"Total return (%): {bt.total_return:.2f}")
    print(f"Max DD (%):       {bt.max_drawdown:.2f}")
    print(f"Win rate:         {bt.win_rate:.2%}")
    print(f"Sharpe:           {bt.sharpe:.2f}")
    print(f"DD limit ({DAILY_DRAWDOWN_LIMIT_PCT:.2f}%%) breached: {breached}")


def _print_regime_results(results: List[RegimeTestResult]) -> None:
    if not results:
        print("\n[RegimeTest] No regimes produced results (insufficient data?).")
        return

    print("\n=== Regime Tests ===")
    for r in results:
        print(f"\nRegime:           {r.regime_name}")
        print(f"Period:           {r.start_date.date()} – {r.end_date.date()}")
        print(f"Total return (%): {r.total_return:.2f}")
        print(f"Max DD (%):       {r.max_drawdown:.2f}")
        print(f"Win rate:         {r.win_rate:.2%}")
        print(f"Sharpe:           {r.sharpe:.2f}")
        print(f"DD limit ({DAILY_DRAWDOWN_LIMIT_PCT:.2f}%%) breached: {r.breached_dd_limit}")


def main() -> int:
    symbol = (UNIVERSE_DEFAULT or ["NVDA"])[0]
    logger.info("Running audit tests for symbol=%s", symbol)

    initial_equity = 100_000.0
    risk_pct = 1.0
    slippage_bps = 1.0

    print(f"[Audit] Symbol={symbol}, initial_equity={initial_equity:,.2f}")

    logger.info("Fetching long history of OHLCV for %s", symbol)
    # Use a large window to attempt to cover 2008 onward; Alpaca may not have
    # data that far back, in which case older slices will be empty.
    df_full = get_ohlcv(symbol, days=365 * 20)
    if df_full is None or getattr(df_full, "empty", True):
        print("ERROR: No OHLCV data returned; aborting audit.")
        return 1

    df_full["date"] = pd.to_datetime(df_full["date"])
    print(
        f"[Audit] OHLCV loaded: {len(df_full)} rows from "
        f"{df_full['date'].iloc[0].date()} to {df_full['date'].iloc[-1].date()}"
    )

    # 1) Yearly backtests
    for year in (2008, 2020, 2022):
        _run_yearly_backtest(symbol, df_full, year, initial_equity, risk_pct, slippage_bps)

    # 2) Regime tests
    logger.info("Running regime tests...")
    regime_results = run_regime_tests(symbol, df_full, initial_equity=initial_equity, risk_per_trade_pct=risk_pct, slippage_bps=slippage_bps)
    _print_regime_results(regime_results)

    # 3) Walk-forward
    logger.info("Running walk-forward test...")
    from dine_trade.backtesting.walk_forward import walk_forward_test  # noqa: E402

    wf = walk_forward_test(
        symbol=symbol,
        ohlcv_df=df_full,
        train_size=252,
        test_size=63,
        initial_equity=initial_equity,
        risk_per_trade_pct=risk_pct,
        slippage_bps=slippage_bps,
    )

    print("\n=== Walk-Forward Summary ===")
    print(f"Windows:          {len(wf.windows)}")
    print(f"Avg return (%):   {wf.avg_return:.2f}")
    print(f"Avg max DD (%):   {wf.avg_max_drawdown:.2f}")
    print(f"Avg Sharpe:       {wf.avg_sharpe:.2f}")

    # 4) Monte Carlo on full backtest over available history
    logger.info("Running full backtest for Monte Carlo...")
    signals_full = generate_signals(
        symbol,
        df_full,
        initial_equity=initial_equity,
        risk_per_trade_pct=risk_pct,
    )
    bt_full = run_backtest(df_full, signals_full, initial_equity=initial_equity, slippage_bps=slippage_bps)

    logger.info("Running Monte Carlo from equity curve...")
    mc = monte_carlo_from_equity(bt_full.equity_curve, n_paths=1000)

    print("\n=== Monte Carlo Summary ===")
    print(f"n_paths:                {mc.n_paths}")
    print(f"DD limit (%):           {mc.dd_limit_pct:.2f}")
    print(f"Failure rate:           {mc.failure_rate:.4f}")
    print(f"Mean max DD (%):        {mc.mean_max_drawdown:.2f}")
    print(f"P05/P50/P95 max DD (%): {mc.p05_max_drawdown:.2f} / {mc.p50_max_drawdown:.2f} / {mc.p95_max_drawdown:.2f}")

    print("\n[Audit] Completed. See console output and logs/audit.log for details.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

