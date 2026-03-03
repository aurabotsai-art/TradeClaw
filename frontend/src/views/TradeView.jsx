import React, { useState } from 'react';
import { useQuery } from '../hooks/useQuery';

function MetricCard({ label, value }) {
  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] px-4 py-3">
      <div className="text-[11px] uppercase tracking-wide text-[var(--text-muted)] mb-1">
        {label}
      </div>
      <div className="text-lg font-mono text-[var(--text-primary)]">{value}</div>
    </div>
  );
}

export default function TradeView() {
  const { data: pnl } = useQuery('/api/monitor/pnl');
  const { data: risk } = useQuery('/api/risk/state');
  const { data: positionsRes } = useQuery('/api/trade/positions');
  const { data: ordersRes } = useQuery('/api/trade/orders');

  const positions = positionsRes?.positions || [];
  const orders = (ordersRes?.orders || []).slice(0, 20);

  const todayPnl = pnl?.today_pnl ?? 0;
  const ddPct = risk?.dd_pct ?? 0;
  const deployed = risk?.deployed_pct ?? 0;

  const [symbol, setSymbol] = useState('');
  const [side, setSide] = useState('BUY');
  const [qty, setQty] = useState(10);
  const [submitting, setSubmitting] = useState(false);

  const handleClosePosition = async (sym) => {
    const ok = window.confirm(`Close position in ${sym}?`);
    if (!ok) return;
    try {
      await fetch(`http://localhost:8000/api/trade/position/${encodeURIComponent(sym)}`, {
        method: 'DELETE',
      });
    } catch {
      // ignore
    }
  };

  const handlePaperTrade = async (e) => {
    e.preventDefault();
    if (!symbol) return;
    setSubmitting(true);
    try {
      await fetch('http://localhost:8000/api/trade/paper', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, side, params: { qty } }),
      });
      setSymbol('');
    } catch {
      // ignore
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 text-[var(--text-primary)] space-y-6">
      <h1 className="font-display text-2xl font-semibold mb-1">Trade</h1>
      <p className="text-[var(--text-secondary)] mb-4">
        Open positions, recent orders, and quick paper trades.
      </p>

      {/* 1. Metric cards row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Today PnL" value={todayPnl} />
        <MetricCard label="Open Positions" value={positions.length} />
        <MetricCard label="Daily DD" value={`${ddPct}%`} />
        <MetricCard label="Capital Deployed" value={`${deployed}%`} />
      </div>

      {/* 2. Open Positions table */}
      <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3">
        <div className="text-[11px] uppercase tracking-wide text-[var(--text-muted)] mb-2">
          Open Positions
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
              <tr>
                <th className="text-left py-1 pr-3 font-normal">Symbol</th>
                <th className="text-left py-1 pr-3 font-normal">Side</th>
                <th className="text-right py-1 pr-3 font-normal">Qty</th>
                <th className="text-right py-1 pr-3 font-normal">Entry</th>
                <th className="text-right py-1 pr-3 font-normal">Current</th>
                <th className="text-right py-1 pr-3 font-normal">Unrealized PnL</th>
                <th className="text-right py-1 pr-3 font-normal">Stop</th>
                <th className="text-right py-1 pr-0 font-normal">Actions</th>
              </tr>
            </thead>
            <tbody>
              {positions.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="py-2 text-center text-[var(--text-muted)] font-mono"
                  >
                    No open positions.
                  </td>
                </tr>
              ) : (
                positions.map((pos) => (
                  <tr key={pos.id ?? pos.symbol} className="border-b border-[var(--border-subtle)]">
                    <td className="py-1 pr-3">{pos.symbol}</td>
                    <td className="py-1 pr-3 text-[var(--text-secondary)]">{pos.side}</td>
                    <td className="py-1 pr-3 text-right font-mono">{pos.qty}</td>
                    <td className="py-1 pr-3 text-right font-mono">{pos.entry_price}</td>
                    <td className="py-1 pr-3 text-right font-mono">{pos.current_price}</td>
                    <td className="py-1 pr-3 text-right font-mono">
                      {pos.unrealized_pnl}
                    </td>
                    <td className="py-1 pr-3 text-right font-mono">{pos.stop_price}</td>
                    <td className="py-1 pr-0 text-right">
                      <button
                        type="button"
                        onClick={() => handleClosePosition(pos.symbol)}
                        className="px-2 py-1 rounded-md border border-[var(--border-subtle)] text-[10px] font-mono text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
                      >
                        Close
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 3. Recent Orders table */}
      <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3">
        <div className="text-[11px] uppercase tracking-wide text-[var(--text-muted)] mb-2">
          Recent Orders
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
              <tr>
                <th className="text-left py-1 pr-3 font-normal">Time</th>
                <th className="text-left py-1 pr-3 font-normal">Symbol</th>
                <th className="text-left py-1 pr-3 font-normal">Side</th>
                <th className="text-right py-1 pr-3 font-normal">Qty</th>
                <th className="text-right py-1 pr-3 font-normal">Price</th>
                <th className="text-left py-1 pr-3 font-normal">Fill Status</th>
                <th className="text-left py-1 pr-3 font-normal">Algo</th>
                <th className="text-right py-1 pr-0 font-normal">PnL</th>
              </tr>
            </thead>
            <tbody>
              {orders.length === 0 ? (
                <tr>
                  <td
                    colSpan={8}
                    className="py-2 text-center text-[var(--text-muted)] font-mono"
                  >
                    No recent orders.
                  </td>
                </tr>
              ) : (
                orders.map((ord) => (
                  <tr key={ord.id} className="border-b border-[var(--border-subtle)]">
                    <td className="py-1 pr-3 text-[var(--text-secondary)]">{ord.time}</td>
                    <td className="py-1 pr-3">{ord.symbol}</td>
                    <td className="py-1 pr-3 text-[var(--text-secondary)]">{ord.side}</td>
                    <td className="py-1 pr-3 text-right font-mono">{ord.qty}</td>
                    <td className="py-1 pr-3 text-right font-mono">{ord.price}</td>
                    <td className="py-1 pr-3 text-[var(--text-secondary)]">{ord.status}</td>
                    <td className="py-1 pr-3 text-[var(--text-secondary)]">{ord.algo}</td>
                    <td className="py-1 pr-0 text-right font-mono">{ord.pnl}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. Paper trade quick input */}
      <form
        onSubmit={handlePaperTrade}
        className="mt-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] px-4 py-3 flex flex-wrap items-center gap-3 text-xs"
      >
        <span className="font-mono text-[var(--text-muted)]">Paper trade</span>
        <input
          type="text"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          placeholder="Symbol"
          className="px-2 py-1 rounded-md bg-[var(--bg-base)] border border-[var(--border-subtle)] text-[var(--text-primary)] font-mono w-20"
        />
        <select
          value={side}
          onChange={(e) => setSide(e.target.value)}
          className="px-2 py-1 rounded-md bg-[var(--bg-base)] border border-[var(--border-subtle)] text-[var(--text-primary)] font-mono"
        >
          <option value="BUY">BUY</option>
          <option value="SELL">SELL</option>
        </select>
        <input
          type="number"
          min={1}
          value={qty}
          onChange={(e) => setQty(Number(e.target.value) || 1)}
          className="px-2 py-1 rounded-md bg-[var(--bg-base)] border border-[var(--border-subtle)] text-[var(--text-primary)] font-mono w-20"
        />
        <button
          type="submit"
          disabled={submitting}
          className="ml-auto px-3 py-1.5 rounded-md bg-[var(--accent)] text-xs font-mono text-white hover:bg-[var(--accent-hover)] disabled:opacity-50"
        >
          {submitting ? 'Submitting…' : 'Submit paper trade'}
        </button>
      </form>
    </div>
  );
}

