import React from 'react';
import { useQuery } from '../../hooks/useQuery';
import { useQuery as _unused } from '../../hooks/useQuery'; // ensure single import usage
import { useWebSocketState } from '../../hooks/useWebSocketState';

// Reuse Section and StatRow semantics via local definitions to avoid circular imports
function Section({ title, children }) {
  return (
    <section className="mb-3">
      <h3 className="text-[11px] font-semibold text-[var(--text-secondary)] mb-1 uppercase tracking-wide">
        {title}
      </h3>
      {children}
    </section>
  );
}

function StatRow({ label, value, color }) {
  const cls =
    color === 'accent'
      ? 'text-[var(--accent)]'
      : color === 'green'
      ? 'text-tc-green'
      : color === 'red'
      ? 'text-tc-red'
      : 'text-[var(--text-primary)]';
  return (
    <div className="flex items-center justify-between text-[11px]">
      <span className="font-mono text-[var(--text-muted)]">{label}</span>
      <span className={`font-mono ${cls}`}>{value}</span>
    </div>
  );
}

function RiskBar({ label, current, max }) {
  const ratio = max ? Math.min(1, (current ?? 0) / max) : 0;
  const pct = Math.round((current ?? 0) * 100) / 100;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="font-mono text-[var(--text-muted)]">{label}</span>
        <span className="font-mono text-[var(--text-secondary)]">
          {pct} / {max}
        </span>
      </div>
      <div className="h-2 rounded-full bg-[var(--bg-raised)] overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{
            width: `${ratio * 100}%`,
            background:
              ratio < 0.7
                ? 'var(--green)'
                : ratio < 1
                ? 'var(--yellow)'
                : 'var(--red)',
          }}
        />
      </div>
    </div>
  );
}

function KillSwitchToggle({ enabled }) {
  const { data } = useQuery('/api/risk/state'); // just for refetch trigger on toggle
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
    <button
      type="button"
      onClick={toggle}
      className={`mt-2 inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[11px] font-mono border ${
        enabled
          ? 'border-red-500/40 bg-red-500/10 text-tc-red'
          : 'border-[var(--border-subtle)] bg-[var(--bg-overlay)] text-[var(--text-secondary)]'
      }`}
    >
      <span>{enabled ? '🔴 Kill Switch ON' : 'Kill Switch OFF'}</span>
    </button>
  );
}

export default function RiskTab() {
  const { data: risk, loading } = useQuery('/api/risk/state');
  const state = useWebSocketState('/ws/state'); // for live dd_pct if desired

  if (loading && !risk) {
    return <div className="text-[11px] text-[var(--text-muted)]">Loading risk state…</div>;
  }

  const r = risk || {};
  const ddPct = state.dd_pct ?? r.dd_pct ?? 0;

  return (
    <div className="flex flex-col gap-3 text-xs text-[var(--text-secondary)]">
      <Section title="Risk Meters">
        <RiskBar label="Daily Drawdown" current={ddPct} max={1.5} />
        <RiskBar label="Capital Deployed" current={r.deployed_pct ?? 0} max={60} />
        <RiskBar label="Correlation Exposure" current={r.corr_max ?? 0} max={0.85} />
        <RiskBar label="Avg Slippage (bps)" current={r.slippage ?? 0} max={5} />
      </Section>

      <Section title="Kelly Sizing Today">
        <StatRow label="EQUITY" value={`$${r.equity ?? 0}`} />
        <StatRow label="1% RISK =" value={`$${r.risk_per_trade ?? 0}`} />
        <StatRow label="WIN_RATE" value={`${r.win_rate ?? 0}%`} />
        <StatRow label="AVG_WIN" value={`$${r.avg_win ?? 0}`} color="green" />
        <StatRow label="AVG_LOSS" value={`$${r.avg_loss ?? 0}`} color="red" />
        <StatRow
          label="KELLY_F"
          value={`${r.kelly_f ?? 0} (½ Kelly)`}
          color="accent"
        />
      </Section>

      <KillSwitchToggle enabled={r.kill_switch ?? false} />
    </div>
  );
}

