# UI-2.1 Chat Orchestrator — intent, tools, Gemini stream, SSE events
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

# ── READ TOOLS (stubs: wire to dine_trade / API) ────────────────────────────


async def fetch_symbol_snapshot(args: dict, mode: str) -> dict:
    """OHLCV + price + news."""
    return {"symbol": args.get("symbol", ""), "ohlcv": {}, "price": None, "headlines": []}


async def get_trade_history(args: dict, mode: str) -> dict:
    """Supabase trade_log."""
    return {"trades": []}


async def get_drawdown_state(args: dict, mode: str) -> dict:
    """Equity, DD, CB flag."""
    return {"equity": 0, "dd_pct": 0, "cb_fired": False}


async def get_positions(args: dict, mode: str) -> dict:
    """Open positions."""
    return {"positions": []}


async def run_consensus_analysis(args: dict, mode: str) -> dict:
    """Agents, no execution."""
    return {"symbol": args.get("symbol", ""), "agents": [], "consensus": None}


async def get_backtest_results(args: dict, mode: str) -> dict:
    """Saved backtest data."""
    return {"results": []}


async def get_whale_prints(args: dict, mode: str) -> dict:
    """Dark pool feed."""
    return {"symbol": args.get("symbol", ""), "whales": []}


async def get_sec_filings(args: dict, mode: str) -> dict:
    """EDGAR watcher."""
    return {"symbol": args.get("symbol", ""), "filings": []}


async def get_macro_events(args: dict, mode: str) -> dict:
    """FOMC, CPI calendar."""
    return {"events": []}


async def classify_regime(args: dict, mode: str) -> dict:
    """Market regime."""
    return {"regime": "unknown", "confidence": 0}


async def get_agent_weights(args: dict, mode: str) -> dict:
    """IC scores."""
    return {"weights": {}}


async def get_tca_summary(args: dict, mode: str) -> dict:
    """Slippage analysis."""
    return {"summary": {}}


# ── ACTION TOOLS (Paper mode only) ─────────────────────────────────────────


async def risk_first_trade(args: dict, mode: str) -> dict:
    """Full pipeline."""
    return {"symbol": args.get("symbol", ""), "status": "stub", "verdict": "pending"}


async def close_position(args: dict, mode: str) -> dict:
    """Close open position."""
    return {"symbol": args.get("symbol", ""), "closed": False}


async def cancel_order(args: dict, mode: str) -> dict:
    """Cancel pending order."""
    return {"order_id": args.get("order_id", ""), "cancelled": False}


# ── ADMIN TOOLS (explicit user action only) ─────────────────────────────────


async def toggle_kill_switch(args: dict, mode: str) -> dict:
    """Emergency stop."""
    return {"enabled": args.get("enabled", False), "status": "ok"}


async def run_backtest_async(args: dict, mode: str) -> dict:
    """Trigger backtest."""
    return {"id": "stub-backtest-id", "status": "queued"}


async def update_universe(args: dict, mode: str) -> dict:
    """Add/remove symbols."""
    return {"action": args.get("action", "add"), "symbol": args.get("symbol", ""), "ok": True}


# ── TOOL REGISTRY ───────────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, Any] = {
    "fetch_symbol_snapshot": fetch_symbol_snapshot,
    "get_trade_history": get_trade_history,
    "get_drawdown_state": get_drawdown_state,
    "get_positions": get_positions,
    "run_consensus_analysis": run_consensus_analysis,
    "get_backtest_results": get_backtest_results,
    "get_whale_prints": get_whale_prints,
    "get_sec_filings": get_sec_filings,
    "get_macro_events": get_macro_events,
    "classify_regime": classify_regime,
    "get_agent_weights": get_agent_weights,
    "get_tca_summary": get_tca_summary,
    "risk_first_trade": risk_first_trade,
    "close_position": close_position,
    "cancel_order": cancel_order,
    "toggle_kill_switch": toggle_kill_switch,
    "run_backtest": run_backtest_async,
    "update_universe": update_universe,
}

READ_TOOLS = {
    "fetch_symbol_snapshot",
    "get_trade_history",
    "get_drawdown_state",
    "get_positions",
    "run_consensus_analysis",
    "get_backtest_results",
    "get_whale_prints",
    "get_sec_filings",
    "get_macro_events",
    "classify_regime",
    "get_agent_weights",
    "get_tca_summary",
}
ACTION_TOOLS = {"risk_first_trade", "close_position", "cancel_order"}
ADMIN_TOOLS = {"toggle_kill_switch", "run_backtest", "update_universe"}


# ── INTENT DETECTION (UI-2.2) ──────────────────────────────────────────────

INTENT_PATTERNS: dict[str, list[str]] = {
    "analysis": ["analyze", "what", "explain", "tell me", "show", "how is"],
    "trade": ["trade", "buy", "sell", "paper trade", "enter", "position"],
    "monitoring": ["pnl", "portfolio", "drawdown", "positions", "equity", "performance"],
    "backtest": ["backtest", "regime", "2022", "simulate", "historical"],
    "intelligence": ["whale", "sec", "dark pool", "filing", "earnings", "insider"],
    "regime": ["regime", "trending", "ranging", "market condition", "vix"],
    "risk": ["risk", "stop loss", "kelly", "circuit breaker", "kill switch"],
    "universe": ["add symbol", "remove", "universe", "track", "watchlist"],
}


def detect_intent(message: str) -> str:
    message_lower = message.lower()
    for intent, keywords in INTENT_PATTERNS.items():
        if any(k in message_lower for k in keywords):
            return intent
    return "general"


# ── SESSION & PROMPT HELPERS (stubs) ────────────────────────────────────────


async def get_session_history(session_id: str) -> list[dict]:
    """Load conversation history from Supabase. Stub: return empty."""
    return []


def _get_kill_switch_active() -> bool:
    """Stub: read from Redis when wired."""
    return False


def build_system_prompt(mode: str, intent: str) -> str:
    """UI-2.4 System prompt for TradeClaw."""
    kill_switch_active = _get_kill_switch_active()
    return f"""You are TradeClaw, an AI trading assistant built on the DineTrade V2 system.
You manage a multi-agent trading bot with: Researcher (gemini-1.5-pro), Sentiment (gemini-1.5-flash),
Chartist (gemini-1.5-flash), Risk Officer (rule-based), and Executor.

CURRENT MODE: {mode.upper()}
{"⚡ Paper trading is ENABLED. You can execute trades." if mode == "paper" else "🔍 Analysis only. No trade execution."}

CAPITAL: $10,000 | DAILY DD LIMIT: 1.5% | PER TRADE RISK: 1%
KILL SWITCH: {"OFF — trading active" if not kill_switch_active else "🔴 ON — ALL TRADING HALTED"}

RULES:
- Always run DataValidator before any trade (two price sources within 0.1%)
- Always run Risk Officer check before any trade execution
- Never suggest bypassing circuit breakers or risk limits
- Always show agent verdicts transparently
- When a trade is rejected, clearly explain why (which agent vetoed, which limit was hit)
- Use tool calls to fetch real data — never make up prices or PnL figures
- Stream your reasoning naturally, like a conversation

When showing tool calls, format them clearly so the user understands what the system is doing.
After every trade, summarize: symbol, side, qty, entry, stop, target, R:R ratio, Kelly size.
"""


def get_tools_for_mode(mode: str) -> dict[str, Any]:
    """Read tools always; action tools in paper/live; admin always (explicit user action)."""
    tools = {k: v for k, v in TOOL_REGISTRY.items() if k in READ_TOOLS}
    if mode in ("paper", "live"):
        for k in ACTION_TOOLS:
            if k in TOOL_REGISTRY:
                tools[k] = TOOL_REGISTRY[k]
    for k in ADMIN_TOOLS:
        if k in TOOL_REGISTRY:
            tools[k] = TOOL_REGISTRY[k]
    return tools


# ── GEMINI STREAM STUB (wire to real GenAI when ready) ──────────────────────


async def stream_gemini_with_tools(
    system_prompt: str,
    history: list[dict],
    message: str,
    available_tools: dict[str, Any],
) -> AsyncGenerator[dict, None]:
    """
    Stub: yields token events. Replace with real Gemini 1.5 Pro with tool calling.
    """
    # Simulate streaming tokens
    reply = (
        f"I received your message about: \"{message[:80]}...\" (analysis mode). "
        "Use the available tools to fetch live data when you need it."
    )
    for word in reply.split():
        await asyncio.sleep(0.02)
        yield {"type": "token", "content": word + " "}
    # Optionally yield a tool_call for testing (e.g. fetch_symbol_snapshot)
    # yield {"type": "tool_call", "name": "fetch_symbol_snapshot", "args": {"symbol": "NVDA"}}


# ── TOOL EXECUTION ──────────────────────────────────────────────────────────


async def execute_tool(tool_name: str, tool_args: dict, mode: str) -> dict:
    """Look up tool in registry and run it. Action tools blocked in analysis."""
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {tool_name}"}
    if tool_name in ACTION_TOOLS and mode == "analysis":
        return {"error": "Trade execution blocked in Analysis mode"}
    fn = TOOL_REGISTRY[tool_name]
    try:
        result = await fn(tool_args, mode)
        return result
    except Exception as e:
        return {"error": str(e)}


# ── SESSION PERSISTENCE (stub) ───────────────────────────────────────────────


async def save_session_message(session_id: str, role: str, content: str) -> None:
    """Save to Supabase chat_sessions. Stub: no-op until wired."""
    pass


# ── MAIN ORCHESTRATOR (UI-2.1) ───────────────────────────────────────────────


async def handle_message(
    session_id: str,
    message: str,
    mode: str,
) -> AsyncGenerator[dict, None]:
    """
    Main orchestrator. Yields SSE events:
      token, tool_start, tool_result, agent_result, trade_result, done
    """
    intent = detect_intent(message)
    history = await get_session_history(session_id)
    system_prompt = build_system_prompt(mode, intent)
    available_tools = get_tools_for_mode(mode)

    assembled_tokens: list[str] = []

    async for event in stream_gemini_with_tools(
        system_prompt, history, message, available_tools
    ):
        yield event

        if event.get("type") == "token":
            assembled_tokens.append(event.get("content", ""))

        if event.get("type") == "tool_call":
            tool_name = event.get("name", "")
            tool_args = event.get("args") or {}
            yield {"type": "tool_start", "name": tool_name, "args": tool_args}
            result = await execute_tool(tool_name, tool_args, mode)
            yield {"type": "tool_result", "name": tool_name, "data": result}

    assembled_response = "".join(assembled_tokens)
    await save_session_message(session_id, "user", message)
    await save_session_message(session_id, "assistant", assembled_response)

    yield {"type": "done"}
