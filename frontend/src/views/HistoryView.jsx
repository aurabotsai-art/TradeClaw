import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DEMO_SESSIONS } from '../demoSessions';

const MESSAGE_MAX_LEN = 96;

function truncate(text) {
  if (!text) return '';
  return text.length <= MESSAGE_MAX_LEN ? text : `${text.slice(0, MESSAGE_MAX_LEN - 3)}...`;
}

function formatTimestamp(ts) {
  if (!ts) return '';
  const d = typeof ts === 'number' ? new Date(ts) : new Date(ts);
  return d.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function groupByDateRange(sessions) {
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const oneDay = 24 * 60 * 60 * 1000;
  const yesterdayStart = todayStart - oneDay;
  const weekStart = todayStart - 6 * oneDay;

  const groups = { today: [], yesterday: [], thisWeek: [], older: [] };

  (sessions || []).forEach((s) => {
    const t = typeof s.timestamp === 'number' ? s.timestamp : new Date(s.timestamp).getTime();
    if (t >= todayStart) groups.today.push(s);
    else if (t >= yesterdayStart) groups.yesterday.push(s);
    else if (t >= weekStart) groups.thisWeek.push(s);
    else groups.older.push(s);
  });

  return groups;
}

function PnLTag({ value }) {
  if (value == null) {
    return <span className="text-xs text-[var(--text-muted)]">No trades</span>;
  }
  const isPositive = value >= 0;
  const sign = isPositive ? '+' : '';
  return (
    <span
      className={`text-xs font-mono ${
        isPositive ? 'text-emerald-400' : 'text-rose-400'
      }`}
    >
      {sign}
      {value.toFixed(2)}
    </span>
  );
}

function ModeBadge({ mode }) {
  if (!mode) return null;
  const base =
    'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ring-1 ring-inset';
  if (mode === 'Live') {
    return (
      <span className={`${base} bg-rose-500/10 text-rose-300 ring-rose-500/40`}>
        Live
      </span>
    );
  }
  if (mode === 'Paper') {
    return (
      <span className={`${base} bg-sky-500/10 text-sky-300 ring-sky-500/40`}>
        Paper
      </span>
    );
  }
  return (
    <span className={`${base} bg-amber-500/10 text-amber-200 ring-amber-500/40`}>
      Analysis
    </span>
  );
}

function SessionSection({ label, sessions, onOpen }) {
  if (!sessions?.length) return null;
  return (
    <section className="mb-6">
      <h2 className="mb-2 text-xs font-semibold tracking-wide text-[var(--text-muted)]">
        {label}
      </h2>
      <div className="space-y-2">
        {sessions.map((s) => (
          <article
            key={s.id}
            className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-raised)]/60 px-4 py-3 hover:border-[var(--border-strong)] hover:bg-[var(--bg-raised)] transition-colors"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                  {truncate(s.firstMessage || s.title)}
                </p>
                <p className="mt-1 text-xs text-[var(--text-secondary)]">
                  {formatTimestamp(s.timestamp)}
                </p>
              </div>
              <div className="flex flex-col items-end gap-1">
                <ModeBadge mode={s.mode} />
                <PnLTag value={s.pnl} />
              </div>
            </div>
            <div className="mt-3 flex items-center justify-between gap-3">
              <p className="text-xs text-[var(--text-muted)] truncate">
                {s.title}
              </p>
              <button
                type="button"
                onClick={() => onOpen?.(s)}
                className="inline-flex items-center rounded-md border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2.5 py-1 text-xs font-medium text-[var(--text-primary)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] transition-colors"
              >
                Open
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default function HistoryView() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return DEMO_SESSIONS;
    return DEMO_SESSIONS.filter((s) => {
      const haystack = `${s.title || ''} ${s.firstMessage || ''}`.toLowerCase();
      return haystack.includes(q);
    });
  }, [query]);

  const groups = useMemo(() => groupByDateRange(filtered), [filtered]);

  const handleOpenSession = (session) => {
    // Navigate back to main chat; in a full implementation we would
    // hydrate the conversation by ID from persistence.
    navigate('/', { state: { sessionId: session.id } });
  };

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(DEMO_SESSIONS, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'session_history.json';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex h-full flex-col px-6 py-5 text-[var(--text-primary)]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-xl font-semibold">History</h1>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">
            Browse past sessions, filter by keyword, and reopen or export runs.
          </p>
        </div>
        <button
          type="button"
          onClick={handleExport}
          className="inline-flex items-center rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-raised)] px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] shadow-sm hover:border-[var(--border-strong)] hover:bg-[var(--bg-hover)] transition-colors"
        >
          Export JSON
        </button>
      </div>

      <div className="mb-5">
        <div className="relative">
          <input
            type="search"
            placeholder="Search sessions by keyword..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:border-[var(--border-strong)] focus:outline-none focus:ring-0"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto pb-6">
        <SessionSection
          label="TODAY"
          sessions={groups.today}
          onOpen={handleOpenSession}
        />
        <SessionSection
          label="YESTERDAY"
          sessions={groups.yesterday}
          onOpen={handleOpenSession}
        />
        <SessionSection
          label="THIS WEEK"
          sessions={groups.thisWeek}
          onOpen={handleOpenSession}
        />
        <SessionSection
          label="OLDER"
          sessions={groups.older}
          onOpen={handleOpenSession}
        />
        {!filtered.length && (
          <p className="mt-8 text-sm text-[var(--text-muted)]">
            No sessions match your search.
          </p>
        )}
      </div>
    </div>
  );
}

