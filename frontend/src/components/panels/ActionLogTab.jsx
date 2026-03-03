import React from 'react';
import { useWebSocketState } from '../../hooks/useWebSocketState';

function LogEntry({ entry }) {
  const statusClass =
    entry.status === 'error'
      ? 'text-tc-red'
      : entry.status === 'warn'
      ? 'text-yellow-400'
      : 'text-tc-green';

  return (
    <div className="flex items-start gap-2 text-[11px] text-[var(--text-secondary)]">
      <span className="font-mono text-[var(--text-muted)] w-10 flex-shrink-0">
        {entry.time}
      </span>
      <span className="w-4 flex-shrink-0" aria-hidden>
        {entry.icon}
      </span>
      <span className={`flex-1 font-mono ${statusClass}`}>{entry.text}</span>
    </div>
  );
}

export default function ActionLogTab() {
  const logsRaw = useWebSocketState('/ws/logs');
  const entries = Array.isArray(logsRaw)
    ? logsRaw
    : Array.isArray(logsRaw?.entries)
    ? logsRaw.entries
    : [];

  return (
    <div className="action-log flex flex-col gap-1">
      {entries.map((entry) => (
        <LogEntry key={entry.id ?? `${entry.time}-${entry.text}`} entry={entry} />
      ))}
      {entries.length === 0 && (
        <div className="text-[11px] text-[var(--text-muted)]">No recent activity.</div>
      )}
    </div>
  );
}

