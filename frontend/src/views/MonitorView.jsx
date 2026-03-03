import React, { useEffect, useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Area,
  BarChart,
  Bar,
  ReferenceLine,
} from 'recharts';

function Card({ title, value, sub }) {
  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] px-4 py-3">
      <div className="text-[11px] uppercase tracking-wide text-[var(--text-muted)] mb-1">
        {title}
      </div>
      <div className="text-lg font-mono text-[var(--text-primary)]">{value}</div>
      {sub && <div className="text-[11px] text-[var(--text-secondary)] mt-0.5">{sub}</div>}
    </div>
  );
}

export default function MonitorView() {
  const [equityCurve, setEquityCurve] = useState([]);
  const [dailyPnl, setDailyPnl] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [tca, setTca] = useState(null);

  useEffect(() => {
    const base = 'http://localhost:8000';
    const fetchAll = async () => {
      try {
        const [curveRes, metricsRes, tcaRes] = await Promise.all([
          fetch(`${base}/api/monitor/equity-curve`),
          fetch(`${base}/api/monitor/metrics`),
          fetch(`${base}/api/monitor/tca`),
        ]);
        const curveJson = await curveRes.json();
        const metricsJson = await metricsRes.json();
        const tcaJson = await tcaRes.json();
        setEquityCurve(curveJson.curve || []);
        setDailyPnl(curveJson.daily || []);
        setMetrics(metricsJson);
        setTca(tcaJson.summary || tcaJson);
      } catch {
        // leave defaults
      }
    };
    fetchAll();
  }, []);

  const kpiSharpe = metrics?.sharpe ?? 0;
  const kpiWinRate = metrics?.win_rate ?? 0;
  const kpiAvgWin = metrics?.avg_win ?? 0;
  const kpiAvgLoss = metrics?.avg_loss ?? 0;
  const maxEquity = equityCurve.reduce(
    (max, p) => (p.equity > max ? p.equity : max),
    equityCurve[0]?.equity ?? 0
  );
  const minEquity = equityCurve.reduce(
    (min, p) => (p.equity < min ? p.equity : min),
    equityCurve[0]?.equity ?? 0
  );
  const maxDrawdown = maxEquity && minEquity ? ((maxEquity - minEquity) / maxEquity) * 100 : 0;

  const agentRows = []; // wire to /api/agents/weights when ready

  return (
    <div className="p-6 text-[var(--text-primary)] space-y-6">
      <h1 className="font-display text-2xl font-semibold mb-1">Monitor</h1>
      <p className="text-[var(--text-secondary)] mb-4">
        Strategy performance, equity, PnL, agents, and TCA.
      </p>

      {/* 1. KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <Card title="Equity" value={equityCurve[equityCurve.length - 1]?.equity ?? 0} />
        <Card title="Sharpe (30d)" value={kpiSharpe.toFixed?.(2) ?? kpiSharpe} />
        <Card title="Max Drawdown" value={`${maxDrawdown.toFixed?.(2) ?? maxDrawdown}%`} />
        <Card title="Win Rate" value={`${kpiWinRate.toFixed?.(1) ?? kpiWinRate}%`} />
        <Card title="Avg Winner" value={kpiAvgWin} />
        <Card title="Avg Loser" value={kpiAvgLoss} />
      </div>

      {/* 2. Equity curve chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3">
          <div className="text-[11px] uppercase tracking-wide text-[var(--text-muted)] mb-1">
            Equity Curve (30d)
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={equityCurve}>
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
                <Area
                  type="monotone"
                  dataKey="equity"
                  stroke="none"
                  fill="rgba(255,255,255,0.03)"
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

        {/* 3. Daily PnL bar chart */}
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3">
          <div className="text-[11px] uppercase tracking-wide text-[var(--text-muted)] mb-1">
            Daily PnL
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dailyPnl}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <ReferenceLine y={0} stroke="#4b5563" />
                <Tooltip
                  contentStyle={{
                    background: '#111827',
                    border: '1px solid #374151',
                    fontSize: 12,
                  }}
                />
                <Bar
                  dataKey="pnl"
                  shape={(props) => {
                    const { fill, x, y, width, height, payload } = props;
                    const positive = payload.pnl >= 0;
                    const color = positive ? '#4ade80' : '#f87171';
                    return (
                      <rect
                        x={x}
                        y={y}
                        width={width}
                        height={height}
                        fill={color}
                        rx={2}
                        ry={2}
                      />
                    );
                  }}
                  fill="#22c55e"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 4. Agent performance table */}
      <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3">
        <div className="text-[11px] uppercase tracking-wide text-[var(--text-muted)] mb-2">
          Agent Performance
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead className="text-[var(--text-muted)] border-b border-[var(--border-subtle)]">
              <tr>
                <th className="text-left py-1 pr-4 font-normal">Agent</th>
                <th className="text-left py-1 pr-4 font-normal">Model</th>
                <th className="text-right py-1 pr-4 font-normal">IC (30d)</th>
                <th className="text-right py-1 pr-4 font-normal">Weight</th>
                <th className="text-right py-1 pr-4 font-normal">Accuracy</th>
                <th className="text-right py-1 pr-0 font-normal">Total Trades</th>
              </tr>
            </thead>
            <tbody>
              {agentRows.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="py-2 text-[var(--text-muted)] text-center font-mono"
                  >
                    No agent metrics yet.
                  </td>
                </tr>
              ) : (
                agentRows.map((row) => (
                  <tr key={row.name} className="border-b border-[var(--border-subtle)]">
                    <td className="py-1 pr-4">{row.name}</td>
                    <td className="py-1 pr-4 text-[var(--text-secondary)]">{row.model}</td>
                    <td className="py-1 pr-4 text-right font-mono">{row.ic}</td>
                    <td className="py-1 pr-4 text-right font-mono">{row.weight}</td>
                    <td className="py-1 pr-4 text-right font-mono">{row.accuracy}</td>
                    <td className="py-1 pr-0 text-right font-mono">{row.trades}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. Slippage analysis (TCA) */}
      <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3">
        <div className="text-[11px] uppercase tracking-wide text-[var(--text-muted)] mb-2">
          Slippage Analysis (TCA)
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <Card
            title="Avg Slippage"
            value={tca?.avg_slippage ?? '-'}
            sub="bps or $/share"
          />
          <Card title="Best Execution" value={tca?.best_execution ?? '-'} />
          <Card title="Worst Execution" value={tca?.worst_execution ?? '-'} />
          <Card title="Fill Rate" value={tca?.fill_rate ?? '-'} />
        </div>
      </div>
    </div>
  );
}

