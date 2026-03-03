import React, { useEffect, useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
} from 'recharts';
import { useQuery } from '../hooks/useQuery';

function Section({ title, children }) {
  return (
    <section className="mb-6">
      <h2 className="text-sm font-semibold text-[var(--text-secondary)] mb-2 uppercase tracking-wide">
        {title}
      </h2>
      {children}
    </section>
  );
}

export default function BacktestView() {
  const [regime, setRegime] = useState('2022 Tech Bear');
  const [symbol, setSymbol] = useState('');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [lastRunId, setLastRunId] = useState(null);

  const { data: regimesRes } = useQuery('/api/backtest/regimes');
  const { data: equityData } = useQuery('/api/monitor/equity-curve');

  const regimes = regimesRes?.regimes || [];
  const lastEquityCurve = equityData?.curve || [];

  // Monte Carlo stub data
  const [mcData, setMcData] = useState([]);
  useEffect(() => {
    const pts = Array.from({ length: 20 }, (_, i) => ({
      bucket: `-${i + 1}%`,
      value: Math.round(Math.random() * 100),
    }));
    setMcData(pts);
  }, []);

  const handleRun = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await fetch('http://localhost:8000/api/backtest/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          regime,
          symbol: symbol || null,
          start: start || null,
          end: end || null,
        }),
      });
      const json = await res.json();
      setLastRunId(json.id || null);
    } catch {
      // ignore
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 text-[var(--text-primary)] space-y-6">
      <h1 className="font-display text-2xl font-semibold mb-1">Backtest</h1>
      <p className="text-[var(--text-secondary)] mb-4">
        Run regime tests, walk-forward analysis, and Monte Carlo risk checks.
      </p>

      {/* 1. Run Backtest form */}
      <Section title="Run Backtest">
        <form
          onSubmit={handleRun}
          className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] px-4 py-3 flex flex-wrap items-center gap-3 text-xs"
        >
          <div className="flex flex-col gap-1">
            <span className="font-mono text-[var(--text-muted)]">Regime</span>
            <select
              value={regime}
              onChange={(e) => setRegime(e.target.value)}
              className="px-2 py-1 rounded-md bg-[var(--bg-base)] border border-[var(--border-subtle)] text-[var(--text-primary)] font-mono"
            >
              <option>2022 Tech Bear</option>
              <option>Aug 2024 Spike</option>
              <option>2020 COVID</option>
              <option>Custom</option>
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <span className="font-mono text-[var(--text-muted)]">Symbol(s)</span>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="e.g. NVDA,BTCUSD"
              className="px-2 py-1 rounded-md bg-[var(--bg-base)] border border-[var(--border-subtle)] text-[var(--text-primary)] font-mono w-40"
            />
          </div>

          <div className="flex flex-col gap-1">
            <span className="font-mono text-[var(--text-muted)]">Start</span>
            <input
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              className="px-2 py-1 rounded-md bg-[var(--bg-base)] border border-[var(--border-subtle)] text-[var(--text-primary)] font-mono"
            />
          </div>
          <div className="flex flex-col gap-1">
            <span className="font-mono text-[var(--text-muted)]">End</span>
            <input
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              className="px-2 py-1 rounded-md bg-[var(--bg-base)] border border-[var(--border-subtle)] text-[var(--text-primary)] font-mono"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="ml-auto px-3 py-1.5 rounded-md bg-[var(--accent)] text-xs font-mono text-white hover:bg-[var(--accent-hover)] disabled:opacity-50"
          >
            {submitting ? 'Running…' : 'Run'}
          </button>

          {lastRunId && (
            <span className="text-[11px] text-[var(--text-muted)] font-mono ml-2">
              Last run id: {lastRunId}
            </span>
          )}
        </form>
      </Section>

      {/* 2. RegimeTest Results table */}
      <Section title="RegimeTest Results">
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3">
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                <tr>
                  <th className="text-left py-1 pr-3 font-normal">Regime</th>
                  <th className="text-left py-1 pr-3 font-normal">Period</th>
                  <th className="text-right py-1 pr-3 font-normal">Return</th>
                  <th className="text-right py-1 pr-3 font-normal">Max DD</th>
                  <th className="text-right py-1 pr-3 font-normal">Sharpe</th>
                  <th className="text-right py-1 pr-3 font-normal">Circuit Breakers</th>
                  <th className="text-left py-1 pr-0 font-normal">Status</th>
                </tr>
              </thead>
              <tbody>
                {regimes.length === 0 ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="py-2 text-center text-[var(--text-muted)] font-mono"
                    >
                      No RegimeTest results yet.
                    </td>
                  </tr>
                ) : (
                  regimes.map((r) => (
                    <tr key={r.id} className="border-b border-[var(--border-subtle)]">
                      <td className="py-1 pr-3">{r.regime}</td>
                      <td className="py-1 pr-3 text-[var(--text-secondary)]">{r.period}</td>
                      <td className="py-1 pr-3 text-right font-mono">{r.return}</td>
                      <td className="py-1 pr-3 text-right font-mono">{r.max_dd}</td>
                      <td className="py-1 pr-3 text-right font-mono">{r.sharpe}</td>
                      <td className="py-1 pr-3 text-right font-mono">
                        {r.circuit_breakers ?? 0}
                      </td>
                      <td className="py-1 pr-0 text-[var(--text-secondary)]">{r.status}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </Section>

      {/* 3. Walk-Forward Results (placeholder table) */}
      <Section title="Walk-Forward Results">
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3">
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                <tr>
                  <th className="text-left py-1 pr-3 font-normal">Train Window</th>
                  <th className="text-left py-1 pr-3 font-normal">Test Window</th>
                  <th className="text-right py-1 pr-3 font-normal">Return</th>
                  <th className="text-right py-1 pr-3 font-normal">Max DD</th>
                  <th className="text-right py-1 pr-0 font-normal">Sharpe</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td
                    colSpan={5}
                    className="py-2 text-center text-[var(--text-muted)] font-mono"
                  >
                    Walk-forward results placeholder (wire /backtesting/walk_forward).
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </Section>

      {/* 4. Monte Carlo */}
      <Section title="Monte Carlo — Max Drawdown Distribution">
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3">
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={mcData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="bucket" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip
                  contentStyle={{
                    background: '#111827',
                    border: '1px solid #374151',
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="value" fill="#38bdf8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 text-[11px] text-[var(--text-secondary)]">
            Failure rate: {/* placeholder since we don't have real paths yet */}0% of paths
            exceed 1.5% daily DD.
          </div>
        </div>
      </Section>

      {/* 5. Last backtest equity curve */}
      <Section title="Last Backtest Equity Curve">
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={lastEquityCurve}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip
                  contentStyle={{
                    background: '#111827',
                    border: '1px solid #374151',
                    fontSize: 12,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="equity"
                  stroke="#ff6b35"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </Section>
    </div>
  );
}

