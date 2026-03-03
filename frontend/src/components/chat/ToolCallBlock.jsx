import React, { useState } from 'react';

// Tool name → human label map (UI-3.5)
const TOOL_LABELS = {
  fetch_symbol_snapshot: 'Fetching market data',
  run_consensus_analysis: 'Running agent consensus',
  risk_first_trade: 'Executing risk-first trade',
  get_drawdown_state: 'Checking drawdown state',
  get_whale_prints: 'Scanning dark pool prints',
  get_sec_filings: 'Reading SEC filings',
  classify_regime: 'Classifying market regime',
  run_backtest: 'Running backtest engine',
};

function formatToolName(name) {
  if (!name) return '';
  if (TOOL_LABELS[name]) return TOOL_LABELS[name];
  return name.replace(/_/g, ' ');
}

function formatArgs(args) {
  if (!args || typeof args !== 'object') return '';
  try {
    return JSON.stringify(args);
  } catch {
    return '';
  }
}

function ToolIcon({ name }) {
  let glyph = '🛠';
  if (name?.includes('snapshot') || name?.includes('symbol')) glyph = '📊';
  else if (name?.includes('consensus') || name?.includes('agent')) glyph = '🤝';
  else if (name?.includes('trade')) glyph = '⚡';
  else if (name?.includes('drawdown') || name?.includes('risk')) glyph = '🛡️';
  else if (name?.includes('whale')) glyph = '🐋';
  else if (name?.includes('sec')) glyph = '📑';
  else if (name?.includes('backtest')) glyph = '🧪';

  return (
    <span className="text-sm" aria-hidden>
      {glyph}
    </span>
  );
}

function ChevronIcon({ rotated }) {
  return (
    <svg
      className={`w-3 h-3 ml-1 transition-transform duration-150 ${
        rotated ? 'rotate-90' : ''
      }`}
      viewBox="0 0 20 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <path
        d="M7 5l6 5-6 5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function ToolCallBlock({ toolCall }) {
  const [expanded, setExpanded] = useState(false);
  const { name, args, status, result } = toolCall || {};
  const isRunning = status === 'running';

  return (
    <div
      className="tool-block border rounded-xl overflow-hidden text-xs font-mono"
      style={{
        borderColor: 'var(--border-subtle)',
        background: 'var(--bg-raised)',
        color: 'var(--text-secondary)',
      }}
    >
      <button
        type="button"
        className="tool-header w-full flex items-center gap-2 px-3 py-2"
        style={{
          background: 'var(--bg-overlay)',
          color: 'var(--text-secondary)',
        }}
        onClick={() => setExpanded((v) => !v)}
      >
        <ToolIcon name={name} />
        <span className="text-[var(--text-primary)] truncate">
          {formatToolName(name)}
        </span>
        <span className="text-[var(--text-muted)] ml-1 truncate">
          ({formatArgs(args)})
        </span>
        <span
          className={`ml-auto px-2 py-0.5 rounded-full border text-[0.65rem] ${
            isRunning
              ? 'border-[var(--accent)] text-[var(--accent)]'
              : 'border-[var(--green)] text-[var(--green)]'
          }`}
        >
          {isRunning ? '⟳ running' : '✓ done'}
        </span>
        <ChevronIcon rotated={expanded} />
      </button>

      {expanded && (
        <div
          className="tool-body px-3 py-2 overflow-x-auto"
          style={{ color: 'var(--text-secondary)' }}
        >
          {result != null && (
            <pre className="whitespace-pre-wrap">
              {typeof result === 'string'
                ? result
                : JSON.stringify(result, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

