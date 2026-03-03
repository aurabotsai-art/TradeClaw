import React from 'react';

function Stat({ label, value, color }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">
        {label}
      </div>
      <div className={`mt-0.5 text-xs font-mono ${color ?? ''}`}>{value}</div>
    </div>
  );
}

export default function TradeCard({ trade }) {
  if (!trade) return null;

  const pnlColor =
    typeof trade.unrealized_pnl === 'number' && trade.unrealized_pnl < 0
      ? 'text-tc-red'
      : 'text-tc-green';

  return (
    <div
      className="trade-card border rounded-2xl p-4 my-2"
      style={{ borderColor: 'var(--border-default)', background: 'var(--bg-overlay)' }}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="font-display font-black text-xl">{trade.symbol}</span>
        <span
          className={`px-2 py-1 rounded-lg text-xs font-mono ${
            trade.side === 'BUY'
              ? 'bg-green-500/10 text-tc-green'
              : 'bg-red-500/10 text-tc-red'
          }`}
        >
          {trade.side}
        </span>
      </div>
      <div className="grid grid-cols-4 gap-3 text-xs">
        <Stat label="Qty" value={trade.qty} />
        <Stat label="Entry" value={trade.entry_price != null ? `$${trade.entry_price}` : '-'} />
        <Stat
          label="Stop"
          value={trade.stop_price != null ? `$${trade.stop_price}` : '-'}
          color="text-tc-red"
        />
        <Stat
          label="Target"
          value={trade.target_price != null ? `$${trade.target_price}` : '-'}
          color="text-tc-green"
        />
        <Stat
          label="Risk"
          value={
            trade.risk_amount != null
              ? `$${trade.risk_amount}${trade.risk_pct ? ` (${trade.risk_pct}%)` : ''}`
              : '-'
          }
        />
        <Stat label="R:R" value={trade.rr_ratio != null ? `${trade.rr_ratio}x` : '-'} />
        <Stat label="Kelly" value={trade.kelly_size != null ? `$${trade.kelly_size}` : '-'} />
        <Stat label="Algo" value={trade.algo || '-'} />
      </div>
      {typeof trade.unrealized_pnl === 'number' && (
        <div className={`mt-3 text-xs font-mono ${pnlColor}`}>
          Unrealized PnL: ${trade.unrealized_pnl}
        </div>
      )}
    </div>
  );
}

