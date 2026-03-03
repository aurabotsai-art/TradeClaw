"""Streamlit dashboard: equity curve, positions, trades, agents, system status.

Run with:
    streamlit run monitoring/dashboard.py
"""
from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
import streamlit as st

from dine_trade.storage.supabase_client import _get_client

logger = logging.getLogger(__name__)


@st.cache_data(ttl=5)
def _load_equity_curve() -> pd.DataFrame:
    try:
        client = _get_client()
    except RuntimeError:
        return pd.DataFrame(columns=["timestamp", "equity", "drawdown_pct"])
    resp = client.table("equity_curve").select("*").order("timestamp", desc=False).limit(1000).execute()
    data = resp.data or []
    if not data:
        return pd.DataFrame(columns=["timestamp", "equity", "drawdown_pct"])
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


@st.cache_data(ttl=5)
def _load_recent_trades(limit: int = 50) -> pd.DataFrame:
    try:
        client = _get_client()
    except RuntimeError:
        return pd.DataFrame()
    resp = client.table("trade_log").select("*").order("created_at", desc=True).limit(limit).execute()
    data = resp.data or []
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])
    return df


@st.cache_data(ttl=5)
def _load_agent_runs(limit: int = 100) -> pd.DataFrame:
    try:
        client = _get_client()
    except RuntimeError:
        return pd.DataFrame()
    resp = client.table("agent_runs").select("*").order("created_at", desc=True).limit(limit).execute()
    data = resp.data or []
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])
    return df


def main() -> None:
    st.set_page_config(page_title="DineTrade Dashboard", layout="wide")
    st.title("DineTrade Live Dashboard")

    # Auto-refresh every 10 seconds
    st.caption(f"Last refreshed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    st.experimental_rerun  # marker for Streamlit; actual auto-refresh driven by run loop

    eq_df = _load_equity_curve()
    trades_df = _load_recent_trades()
    agents_df = _load_agent_runs()

    # Top row: equity curve and key stats
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Equity Curve")
        if eq_df.empty:
            st.info("No equity_curve data available yet.")
        else:
            st.line_chart(eq_df.set_index("timestamp")["equity"])
    with col2:
        st.subheader("Current Status")
        if eq_df.empty:
            st.metric("Equity", "N/A")
            st.metric("Drawdown %", "N/A")
        else:
            latest = eq_df.iloc[-1]
            st.metric("Equity", f"{latest['equity']:.2f}")
            st.metric("Drawdown %", f"{latest.get('drawdown_pct', 0.0):.2f}%")

    # Recent trades
    st.subheader("Recent Trades")
    if trades_df.empty:
        st.info("No trades logged yet.")
    else:
        cols = [c for c in trades_df.columns if c in {"created_at", "symbol", "side", "qty", "price", "asset_class", "strategy_phase"}]
        st.dataframe(trades_df[cols].head(50))

    # Agent verdicts
    st.subheader("Recent Agent Runs")
    if agents_df.empty:
        st.info("No agent_runs logged yet.")
    else:
        cols = [c for c in agents_df.columns if c in {"created_at", "run_id", "agent_name", "symbol", "verdict", "score"}]
        st.dataframe(agents_df[cols].head(100))


if __name__ == "__main__":
    main()

