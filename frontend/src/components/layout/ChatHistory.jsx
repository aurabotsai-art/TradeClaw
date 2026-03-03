/**
 * UI-0.6 Chat History Left Drawer
 * Width: 260px, slides over sidebar. Backdrop, click-outside / Escape to close.
 */
import React, { useEffect, useCallback } from 'react';

const TITLE_MAX_LEN = 42;

function groupSessionsByDate(sessions) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const oneDay = 24 * 60 * 60 * 1000;
  const yesterday = today - oneDay;
  const weekStart = today - 6 * oneDay;

  const groups = { today: [], yesterday: [], thisWeek: [] };

  (sessions || []).forEach((s) => {
    const t = typeof s.timestamp === 'number' ? s.timestamp : new Date(s.timestamp).getTime();
    if (t >= today) groups.today.push(s);
    else if (t >= yesterday) groups.yesterday.push(s);
    else if (t >= weekStart) groups.thisWeek.push(s);
  });

  return groups;
}

function truncate(title) {
  if (!title) return 'Untitled';
  return title.length <= TITLE_MAX_LEN ? title : title.slice(0, TITLE_MAX_LEN - 3) + '...';
}

function formatTime(timestamp) {
  if (timestamp == null) return '';
  const d = typeof timestamp === 'number' ? new Date(timestamp) : new Date(timestamp);
  const now = new Date();
  const today = now.toDateString() === d.toDateString();
  if (today) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const yesterday = new Date(now.getTime() - 86400000).toDateString() === d.toDateString();
  if (yesterday) return 'Yesterday';
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function Section({ label, items, activeId, onSelect, onClose }) {
  if (!items?.length) return null;
  return (
    <div className="mb-4">
      <div className="px-3 py-1.5 text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">
        {label}
      </div>
      <ul className="space-y-0.5" role="list">
        {items.map((session) => {
          const isActive = session.id === activeId;
          return (
            <li key={session.id}>
              <button
                type="button"
                onClick={() => { onSelect?.(session); onClose?.(); }}
                className={`
                  w-full text-left px-3 py-2.5 rounded-lg transition-colors
                  ${isActive ? 'bg-[var(--bg-hover)] text-[var(--text-primary)]' : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]'}
                `}
              >
                <span className="block text-sm truncate pr-8" title={session.title}>
                  {truncate(session.title)}
                </span>
                <span className="block text-xs text-[var(--text-muted)] mt-0.5">
                  {formatTime(session.timestamp)}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function ChatHistory({
  isOpen = false,
  onClose,
  sessions = [],
  activeSessionId,
  onSelectSession,
}) {
  const groups = groupSessionsByDate(sessions);

  const handleEscape = useCallback(
    (e) => {
      if (e.key === 'Escape') onClose?.();
    },
    [onClose]
  );

  useEffect(() => {
    if (!isOpen) return;
    document.addEventListener('keydown', handleEscape);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, handleEscape]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop — click to close */}
      <div
        className="fixed inset-0 z-40 bg-black/50 transition-opacity"
        aria-hidden="true"
        onClick={onClose}
      />
      {/* Drawer — slides in from left over sidebar */}
      <aside
        className="fixed left-0 top-0 bottom-0 z-50 w-[260px] flex flex-col bg-[var(--bg-raised)] border-r border-[var(--border-subtle)] shadow-xl animate-slide-in-left"
        role="dialog"
        aria-label="Chat history"
      >
        <div className="flex items-center justify-between px-3 py-3 border-b border-[var(--border-subtle)]">
          <h2 className="text-sm font-medium text-[var(--text-primary)]">Chats</h2>
        </div>
        <div className="flex-1 overflow-y-auto py-2">
          <Section
            label="Today"
            items={groups.today}
            activeId={activeSessionId}
            onSelect={onSelectSession}
            onClose={onClose}
          />
          <Section
            label="Yesterday"
            items={groups.yesterday}
            activeId={activeSessionId}
            onSelect={onSelectSession}
            onClose={onClose}
          />
          <Section
            label="This week"
            items={groups.thisWeek}
            activeId={activeSessionId}
            onSelect={onSelectSession}
            onClose={onClose}
          />
          {!groups.today?.length && !groups.yesterday?.length && !groups.thisWeek?.length && (
            <p className="px-3 py-4 text-sm text-[var(--text-muted)]">No recent chats</p>
          )}
        </div>
      </aside>
    </>
  );
}
