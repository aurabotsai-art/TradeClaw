"""Monthly Performance Review Automation (Phase 14.6).

Auto-generates a monthly report including:
  - Total PnL, Sharpe ratio, max drawdown
  - Best and worst trades (with full context)
  - Agent accuracy breakdown (by_agent from strategy_performance or derived from outcomes)
  - Strategy param changes made (from strategy_params)
  - Universe changes made (from universe_candidates / suggest_universe_changes)
  - Benchmark comparison: SPY and BTC (alpha = bot_return - benchmark_return)

Exports as PDF to Supabase storage and sends summary + PDF via Telegram.
"""

from __future__ import annotations

import calendar
import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Supabase storage bucket for reports (create in dashboard if missing)
REPORTS_BUCKET = "reports"

# Optional: reportlab for PDF; fallback to markdown-only
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer  # type: ignore[import]
    _HAS_REPORTLAB = True
except Exception:  # pragma: no cover
    _HAS_REPORTLAB = False


def _month_bounds(year: int, month: int) -> tuple[str, str]:
    """Return (start_iso, end_iso) for the given month in UTC."""
    start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start.isoformat(), end.isoformat()


def _metrics_from_outcomes(outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute total PnL, Sharpe, max drawdown from trade_outcomes list."""
    if not outcomes:
        return {
            "total_pnl": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "n_trades": 0,
            "win_rate": 0.0,
        }
    pnls = []
    for o in outcomes:
        try:
            pnls.append(float(o.get("pnl", 0) or 0))
        except (TypeError, ValueError):
            pnls.append(0.0)
    total_pnl = sum(pnls)
    n = len(pnls)
    wins = [p for p in pnls if p > 0]
    win_rate = len(wins) / n if n else 0.0
    mean_pnl = total_pnl / n if n else 0.0
    variance = sum((p - mean_pnl) ** 2 for p in pnls) / n if n else 0.0
    std_pnl = variance ** 0.5 if variance > 0 else 0.0
    sharpe = (mean_pnl / std_pnl) if std_pnl > 0 else 0.0
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        cum += p
        if cum > peak:
            peak = cum
        max_dd = max(max_dd, peak - cum)
    return {
        "total_pnl": round(total_pnl, 2),
        "sharpe": round(sharpe, 4),
        "max_drawdown": round(max_dd, 2),
        "n_trades": n,
        "win_rate": round(win_rate, 4),
    }


def _agent_accuracy_from_outcomes(outcomes: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Derive per-agent stats from outcomes (agent_verdicts + pnl)."""
    by_agent: Dict[str, List[float]] = {}
    for o in outcomes:
        verdicts = o.get("agent_verdicts") or {}
        try:
            pnl = float(o.get("pnl", 0) or 0)
        except (TypeError, ValueError):
            pnl = 0.0
        for name, data in verdicts.items():
            if not isinstance(data, dict):
                continue
            if name not in by_agent:
                by_agent[name] = []
            by_agent[name].append(pnl)
    result = {}
    for agent, pnls in by_agent.items():
        if not pnls:
            continue
        wins = [p for p in pnls if p > 0]
        result[agent] = {
            "n_trades": len(pnls),
            "win_rate": round(len(wins) / len(pnls), 4),
            "avg_pnl": round(sum(pnls) / len(pnls), 2),
            "total_pnl": round(sum(pnls), 2),
        }
    return result


def fetch_benchmark_returns(year: int, month: int) -> Dict[str, Optional[float]]:
    """Fetch SPY and BTC (BTCUSDT) monthly return in percent. Returns {"SPY": pct, "BTC": pct}."""
    start_iso, end_iso = _month_bounds(year, month)
    result: Dict[str, Optional[float]] = {"SPY": None, "BTC": None}

    try:
        from dine_trade.data.providers import get_ohlcv_with_failover
        df = get_ohlcv_with_failover("SPY", days=35)
        if df is not None and not getattr(df, "empty", True) and "date" in df.columns and "close" in df.columns:
            df = df.copy()
            df["date"] = pd.to_datetime(df["date"])
            df = df[(df["date"] >= start_iso) & (df["date"] <= end_iso)]
            if len(df) >= 2:
                closes = df["close"].astype(float)
                first_c = closes.iloc[0]
                last_c = closes.iloc[-1]
                if first_c and first_c != 0:
                    result["SPY"] = round((last_c / first_c - 1.0) * 100.0, 2)
    except Exception as e:
        logger.warning("Failed to fetch SPY benchmark: %s", e)

    try:
        from dine_trade.data.connectors import binance_connector
        df = binance_connector.get_ohlcv("BTCUSDT", interval="1d", limit=35)
        if df is not None and not getattr(df, "empty", True):
            df = df.copy()
            df["date"] = pd.to_datetime(df["close_time"])
            df = df[(df["date"] >= start_iso) & (df["date"] <= end_iso)]
            if len(df) >= 2:
                closes = df["close"].astype(float)
                first_c = closes.iloc[0]
                last_c = closes.iloc[-1]
                if first_c and first_c != 0:
                    result["BTC"] = round((last_c / first_c - 1.0) * 100.0, 2)
    except Exception as e:
        logger.warning("Failed to fetch BTC benchmark: %s", e)

    return result


def get_monthly_report_data(year: int, month: int) -> Dict[str, Any]:
    """Gather all data needed for the monthly report."""
    start_iso, end_iso = _month_bounds(year, month)

    from dine_trade.storage.supabase_client import (
        select_trade_outcomes_between,
        select_strategy_params_between,
        select_universe_candidates_between,
    )
    from dine_trade.evolution.performance_tracker import compute_strategy_metrics

    outcomes = select_trade_outcomes_between(start_iso, end_iso)
    metrics = _metrics_from_outcomes(outcomes)
    agent_accuracy = _agent_accuracy_from_outcomes(outcomes)

    # Strategy performance (last 30d) for additional Sharpe/drawdown if needed
    try:
        strategy_metrics = compute_strategy_metrics(lookback_days=30)
    except Exception:
        strategy_metrics = {}

    param_changes = select_strategy_params_between(start_iso, end_iso)
    universe_candidates = select_universe_candidates_between(start_iso, end_iso)

    # Best/worst trades by PnL (with full context)
    sorted_outcomes = sorted(
        outcomes,
        key=lambda o: float(o.get("pnl", 0) or 0),
        reverse=True,
    )
    best_trades = sorted_outcomes[:5] if sorted_outcomes else []
    worst_trades = sorted_outcomes[-5:][::-1] if sorted_outcomes else []

    benchmarks = fetch_benchmark_returns(year, month)
    bot_return_pct = 0.0  # We don't have equity curve here; use total_pnl as proxy or add initial_equity
    # Alpha vs SPY: if we had starting equity we'd do (bot_return - spy_return). For now report total_pnl and benchmarks.
    spy_ret = benchmarks.get("SPY") or 0.0
    btc_ret = benchmarks.get("BTC") or 0.0

    return {
        "year": year,
        "month": month,
        "start_iso": start_iso,
        "end_iso": end_iso,
        "metrics": metrics,
        "strategy_metrics": strategy_metrics,
        "agent_accuracy": agent_accuracy,
        "param_changes": param_changes,
        "universe_candidates": universe_candidates,
        "best_trades": best_trades,
        "worst_trades": worst_trades,
        "benchmarks": benchmarks,
        "spy_return_pct": spy_ret,
        "btc_return_pct": btc_ret,
        "outcomes_count": len(outcomes),
    }


def build_report_markdown(data: Dict[str, Any], *, initial_equity: float = 100_000.0) -> str:
    """Build the monthly report as Markdown."""
    m = data["metrics"]
    y, mo = data["year"], data["month"]
    lines = [
        f"# Monthly Performance Review — {y}-{mo:02d}",
        "",
        "## Summary",
        f"- **Total PnL:** {m.get('total_pnl', 0):.2f}",
        f"- **Sharpe (trade-level):** {m.get('sharpe', 0):.4f}",
        f"- **Max drawdown (cumulative PnL):** {m.get('max_drawdown', 0):.2f}",
        f"- **Trades:** {m.get('n_trades', 0)} | **Win rate:** {m.get('win_rate', 0):.1%}",
        "",
        "## Benchmark comparison",
    ]
    spy = data.get("spy_return_pct") or 0
    btc = data.get("btc_return_pct") or 0
    bot_return_pct = (m.get("total_pnl", 0) / initial_equity * 100.0) if initial_equity else 0
    alpha_spy = bot_return_pct - spy
    alpha_btc = bot_return_pct - btc
    lines.extend([
        f"- **SPY return (month):** {spy:.2f}%",
        f"- **BTC return (month):** {btc:.2f}%",
        f"- **Bot return (PnL/equity proxy):** {bot_return_pct:.2f}%",
        f"- **Alpha vs SPY:** {alpha_spy:.2f}%",
        f"- **Alpha vs BTC:** {alpha_btc:.2f}%",
        "",
        "## Agent accuracy breakdown",
    ])
    for agent, stats in (data.get("agent_accuracy") or {}).items():
        lines.append(f"- **{agent}:** n={stats.get('n_trades', 0)}, win_rate={stats.get('win_rate', 0):.1%}, avg_pnl={stats.get('avg_pnl', 0):.2f}, total_pnl={stats.get('total_pnl', 0):.2f}")
    lines.append("")
    lines.append("## Best trades (top 5 by PnL)")
    for i, t in enumerate(data.get("best_trades") or [], 1):
        pnl = t.get("pnl", 0)
        sym = t.get("symbol", "?")
        regime = t.get("market_regime", "?")
        lines.append(f"{i}. {sym} PnL={pnl:.2f} regime={regime}")
    lines.append("")
    lines.append("## Worst trades (bottom 5 by PnL)")
    for i, t in enumerate(data.get("worst_trades") or [], 1):
        pnl = t.get("pnl", 0)
        sym = t.get("symbol", "?")
        regime = t.get("market_regime", "?")
        lines.append(f"{i}. {sym} PnL={pnl:.2f} regime={regime}")
    lines.append("")
    lines.append("## Strategy param changes")
    for row in data.get("param_changes") or []:
        tuned_at = row.get("tuned_at", "")[:19]
        lines.append(f"- {tuned_at}: atr_mult={row.get('atr_mult')}, threshold={row.get('consensus_threshold')}, kelly_cap={row.get('kelly_fraction_cap')}, twap_slices={row.get('twap_slices')}")
    if not (data.get("param_changes")):
        lines.append("- No param changes this month.")
    lines.append("")
    lines.append("## Universe changes (candidates scanned this month)")
    for row in (data.get("universe_candidates") or [])[:15]:
        lines.append(f"- {row.get('symbol')} (score={row.get('score')}, {row.get('asset_class')})")
    if not (data.get("universe_candidates")):
        lines.append("- No universe candidate scans this month.")
    return "\n".join(lines)


def build_report_pdf(markdown_text: str, title: str = "Monthly Performance Review") -> Optional[bytes]:
    """Build a simple PDF from report content. Returns None if reportlab not installed."""
    if not _HAS_REPORTLAB:
        return None
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    for line in markdown_text.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 12))
            continue
        if line.startswith("# "):
            story.append(Paragraph(line[2:], styles["Title"]))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], styles["Heading2"]))
        else:
            story.append(Paragraph(line.replace("<", "&lt;").replace(">", "&gt;"), styles["Normal"]))
        story.append(Spacer(1, 6))
    doc.build(story)
    return buf.getvalue()


def upload_report_to_supabase(
    content: bytes,
    filename: str,
    *,
    bucket: str = REPORTS_BUCKET,
    content_type: str = "application/pdf",
) -> Optional[str]:
    """Upload report bytes to Supabase storage. Returns storage path or None on failure."""
    try:
        from dine_trade.storage.supabase_client import upload_storage_file
        path = f"monthly/{filename}"
        upload_storage_file(bucket, path, content, content_type=content_type)
        return f"{bucket}/{path}"
    except Exception as e:
        logger.warning("Failed to upload report to Supabase storage: %s", e)
        return None


def send_report_telegram(
    summary_text: str,
    pdf_bytes: Optional[bytes] = None,
    filename: str = "monthly_report.pdf",
) -> None:
    """Send report summary via Telegram; optionally attach PDF as document."""
    import os
    import requests
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        logger.info("Telegram not configured; skipping send.")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": summary_text[:4000]}
        resp = requests.post(url, json=payload, timeout=15)
        if not resp.ok:
            logger.warning("Telegram sendMessage failed: %s %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.warning("Telegram sendMessage error: %s", e)
    if pdf_bytes:
        try:
            url_doc = f"https://api.telegram.org/bot{token}/sendDocument"
            files = {"document": (filename, pdf_bytes, "application/pdf")}
            data = {"chat_id": chat_id}
            resp = requests.post(url_doc, data=data, files=files, timeout=30)
            if not resp.ok:
                logger.warning("Telegram sendDocument failed: %s %s", resp.status_code, resp.text[:200])
        except Exception as e:
            logger.warning("Telegram sendDocument error: %s", e)


def run_monthly_review(
    year: int,
    month: int,
    *,
    initial_equity: float = 100_000.0,
    upload_pdf: bool = True,
    send_telegram: bool = True,
) -> Dict[str, Any]:
    """Generate monthly report, optionally export PDF to Supabase and send via Telegram.

    Returns dict with report_data, markdown, pdf_path (if uploaded), telegram_sent.
    """
    data = get_monthly_report_data(year, month)
    markdown = build_report_markdown(data, initial_equity=initial_equity)
    pdf_bytes = build_report_pdf(markdown, title=f"Monthly Review {year}-{month:02d}")
    pdf_path: Optional[str] = None
    if upload_pdf and pdf_bytes:
        filename = f"performance_review_{year}_{month:02d}.pdf"
        pdf_path = upload_report_to_supabase(pdf_bytes, filename)
    elif not pdf_bytes and upload_pdf:
        # Fallback: upload markdown
        filename = f"performance_review_{year}_{month:02d}.md"
        pdf_path = upload_report_to_supabase(
            markdown.encode("utf-8"),
            filename,
            content_type="text/markdown",
        )
    if send_telegram:
        summary = markdown.split("## ")[0] + "\n\n(Full report attached or in storage.)"
        send_report_telegram(summary, pdf_bytes=pdf_bytes, filename=f"review_{year}_{month:02d}.pdf")
    return {
        "report_data": data,
        "markdown": markdown,
        "pdf_path": pdf_path,
        "telegram_sent": send_telegram,
    }
