import React from 'react';
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

function KillSwitchPanel({ enabled, lastToggled }) {
  const toggle = async () => {
    try {
      await fetch('http://localhost:8000/api/risk/kill-switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !enabled }),
      });
    } catch {
      // ignore
    }
  };

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-[var(--text-primary)]">Kill Switch</div>
        <div
          className={`px-2 py-1 rounded-full text-[11px] font-mono ${
            enabled ? 'bg-red-500/10 text-tc-red' : 'bg-green-500/10 text-tc-green'
          }`}
        >
          {enabled ? 'ON' : 'OFF'}
        </div>
      </div>
      <button
        type="button"
        onClick={toggle}
        className={`mt-1 inline-flex items-center justify-center px-4 py-2 rounded-md text-xs font-mono ${
          enabled
            ? 'bg-green-500 text-white hover:bg-green-400'
            : 'bg-red-600 text-white hover:bg-red-500'
        }`}
      >
        {enabled ? 'Turn OFF (resume trading)' : 'Turn ON (halt trading)'}
      </button>
      <div className="text-[11px] text-[var(--text-secondary)] mt-1">
        Last toggled:{' '}
        <span className="font-mono">
          {lastToggled ? new Date(lastToggled).toLocaleString() : 'never'}
        </span>
      </div>
    </div>
  );
}

export default function RiskView() {
  const { data: risk } = useQuery('/api/risk/state');
  const { data: postMortemRes } = useQuery('/api/risk/post-mortem');
  const { data: cbRes } = useQuery('/api/risk/circuit-breakers');

  const r = risk || {};
  const postMortem = postMortemRes?.events || [];
  const cbEvents = cbRes?.events || [];

  return (
    <div className="p-6 text-[var(--text-primary)] space-y-6">
      <h1 className="font-display text-2xl font-semibold mb-1">Risk</h1>
      <p className="text-[var(--text-secondary)] mb-4">
        Risk parameters, kill switch state, and circuit breaker history.
      </p>

      {/* 1. Risk parameter cards */}
      <Section title="Risk Parameters">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard
            label="Daily DD Limit"
            value={`${r.max_dd_limit_pct ?? 1.5}%`}
          />
          <MetricCard
            label="Per Trade Risk"
            value={`${r.per_trade_risk_pct ?? 1.0}% ($${r.risk_per_trade ?? 0})`}
          />
          <MetricCard
            label="Kelly Fraction"
            value={r.kelly_f != null ? `${r.kelly_f}` : '-'}
          />
          <MetricCard
            label="ATR Multiplier"
            value={r.atr_mult != null ? `${r.atr_mult}x` : '-'}
          />
        </div>
      </Section>

      {/* 2. Risk parameters table */}
      <Section title="Risk Parameters Detail">
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3">
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                <tr>
                  <th className="text-left py-1 pr-3 font-normal">Parameter</th>
                  <th className="text-right py-1 pr-3 font-normal">Value</th>
                  <th className="text-right py-1 pr-3 font-normal">Current</th>
                  <th className="text-left py-1 pr-0 font-normal">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[var(--border-subtle)]">
                  <td className="py-1 pr-3">Daily DD Limit</td>
                  <td className="py-1 pr-3 text-right font-mono">
                    {r.max_dd_limit_pct ?? 1.5}%
                  </td>
                  <td className="py-1 pr-3 text-right font-mono">
                    {r.dd_pct != null ? `${r.dd_pct}%` : '-'}
                  </td>
                  <td className="py-1 pr-0 text-[var(--text-secondary)]">OK</td>
                </tr>
                <tr className="border-b border-[var(--border-subtle)]">
                  <td className="py-1 pr-3">Per Trade Risk</td>
                  <td className="py-1 pr-3 text-right font-mono">
                    {r.per_trade_risk_pct ?? 1.0}%
                  </td>
                  <td className="py-1 pr-3 text-right font-mono">
                    ${r.risk_per_trade ?? 0}
                  </td>
                  <td className="py-1 pr-0 text-[var(--text-secondary)]">OK</td>
                </tr>
                <tr className="border-b border-[var(--border-subtle)]">
                  <td className="py-1 pr-3">ATR Multiplier</td>
                  <td className="py-1 pr-3 text-right font-mono">
                    {r.atr_mult != null ? `${r.atr_mult}x` : '-'}
                  </td>
                  <td className="py-1 pr-3 text-right font-mono">-</td>
                  <td className="py-1 pr-0 text-[var(--text-secondary)]">OK</td>
                </tr>
                <tr>
                  <td className="py-1 pr-3">Kelly Fraction</td>
                  <td className="py-1 pr-3 text-right font-mono">
                    {r.kelly_f != null ? r.kelly_f : '-'}
                  </td>
                  <td className="py-1 pr-3 text-right font-mono">
                    ½ Kelly
                  </td>
                  <td className="py-1 pr-0 text-[var(--text-secondary)]">OK</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </Section>

      {/* 3. Kill Switch panel */}
      <Section title="Kill Switch">
        <KillSwitchPanel
          enabled={r.kill_switch ?? false}
          lastToggled={r.kill_switch_last_toggled}
        />
      </Section>

      {/* 4. Post-mortem log */}
      <Section title="Post-Mortem Log">
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3">
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                <tr>
                  <th className="text-left py-1 pr-3 font-normal">Date</th>
                  <th className="text-left py-1 pr-3 font-normal">Triggered At</th>
                  <th className="text-right py-1 pr-3 font-normal">Drawdown</th>
                  <th className="text-right py-1 pr-3 font-normal">Capital At Open</th>
                  <th className="text-left py-1 pr-0 font-normal">Positions Snapshot</th>
                </tr>
              </thead>
              <tbody>
                {postMortem.length === 0 ? (
                  <tr>
                    <td
                      colSpan={5}
                      className="py-2 text-center text-[var(--text-muted)] font-mono"
                    >
                      No post-mortem events yet.
                    </td>
                  </tr>
                ) : (
                  postMortem.map((e) => (
                    <tr key={e.id} className="border-b border-[var(--border-subtle)]">
                      <td className="py-1 pr-3 text-[var(--text-secondary)]">{e.date}</td>
                      <td className="py-1 pr-3 text-[var(--text-secondary)]">
                        {e.triggered_at}
                      </td>
                      <td className="py-1 pr-3 text-right font-mono">{e.drawdown}</td>
                      <td className="py-1 pr-3 text-right font-mono">
                        {e.capital_at_open}
                      </td>
                      <td className="py-1 pr-0 text-[var(--text-secondary)]">
                        {e.positions_snapshot}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </Section>

      {/* 5. Circuit breaker history */}
      <Section title="Circuit Breaker History">
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3">
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                <tr>
                  <th className="text-left py-1 pr-3 font-normal">Time</th>
                  <th className="text-right py-1 pr-3 font-normal">Drawdown</th>
                  <th className="text-left py-1 pr-3 font-normal">Reason</th>
                  <th className="text-left py-1 pr-0 font-normal">Recovery</th>
                </tr>
              </thead>
              <tbody>
                {cbEvents.length === 0 ? (
                  <tr>
                    <td
                      colSpan={4}
                      className="py-2 text-center text-[var(--text-muted)] font-mono"
                    >
                      No circuit breaker events yet.
                    </td>
                  </tr>
                ) : (
                  cbEvents.map((e) => (
                    <tr key={e.id} className="border-b border-[var(--border-subtle)]">
                      <td className="py-1 pr-3 text-[var(--text-secondary)]">{e.time}</td>
                      <td className="py-1 pr-3 text-right font-mono">{e.drawdown}</td>
                      <td className="py-1 pr-3 text-[var(--text-secondary)]">{e.reason}</td>
                      <td className="py-1 pr-0 text-[var(--text-secondary)]">
                        {e.recovery}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </Section>
    </div>
  );
}

