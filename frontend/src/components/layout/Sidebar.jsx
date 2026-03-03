/**
 * UI-0.2 Exact Claude Left Sidebar (icon-only)
 * Width: 48px | Icons: 20px | No text, no labels
 */
import React from 'react';

const ICON_CLASS = 'w-5 h-5'; // 20px

const PlusIcon = () => (
  <svg className={ICON_CLASS} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
  </svg>
);
const SearchIcon = () => (
  <svg className={ICON_CLASS} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);
const BriefcaseIcon = () => (
  <svg className={ICON_CLASS} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
  </svg>
);
const ChatIcon = () => (
  <svg className={ICON_CLASS} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
  </svg>
);
const BookIcon = () => (
  <svg className={ICON_CLASS} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
  </svg>
);
const GridIcon = () => (
  <svg className={ICON_CLASS} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
  </svg>
);
const CodeIcon = () => (
  <svg className={ICON_CLASS} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
  </svg>
);
const DownloadIcon = () => (
  <svg className={ICON_CLASS} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
);

const NAV_ICONS = [
  { id: 'new', icon: PlusIcon, action: 'newChat', tooltip: 'New chat' },
  { id: 'search', icon: SearchIcon, route: '/search', tooltip: 'Search' },
  { id: 'trade', icon: BriefcaseIcon, route: '/trade', tooltip: 'Trade' },
  { id: 'chat', icon: ChatIcon, route: '/chat', tooltip: 'Chats' },
  { id: 'history', icon: BookIcon, route: '/history', tooltip: 'History' },
  { id: 'universe', icon: GridIcon, route: '/universe', tooltip: 'Universe' },
  { id: 'monitor', icon: CodeIcon, route: '/monitor', tooltip: 'Monitor' },
];

export default function Sidebar({
  currentRoute = '',
  onNewChat,
  onNavigate,
  onExportSession,
  onOpenSettings,
}) {
  const handleNav = (item) => {
    if (item.action === 'newChat') {
      onNewChat?.();
      return;
    }
    if (item.route) onNavigate?.(item.route);
  };

  const isActive = (item) => {
    if (item.action === 'newChat') return false;
    return item.route ? currentRoute === item.route : false;
  };

  return (
    <aside
      className="flex flex-col w-12 flex-shrink-0 border-r border-[var(--border-subtle)] bg-[var(--bg-raised)]"
      style={{ width: '48px' }}
      role="navigation"
      aria-label="Main navigation"
    >
      {/* Top: nav icons */}
      <nav className="flex flex-col items-center pt-2 gap-px">
        {NAV_ICONS.map((item) => {
          const Icon = item.icon;
          const active = isActive(item);
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => handleNav(item)}
              title={item.tooltip}
              aria-label={item.tooltip}
              className={`
                flex items-center justify-center w-10 h-10 rounded-lg transition-colors
                ${active ? 'bg-[var(--bg-hover)] text-[var(--text-primary)]' : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]'}
              `}
              style={{ padding: '12px 0' }}
            >
              <Icon />
            </button>
          );
        })}
      </nav>

      {/* Spacer to push bottom items down */}
      <div className="flex-1 min-h-4" />

      {/* Bottom: export + avatar */}
      <div className="flex flex-col items-center pb-3 gap-px">
        <button
          type="button"
          onClick={onExportSession}
          title="Export session"
          aria-label="Export session"
          className="flex items-center justify-center w-10 h-10 rounded-lg text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] transition-colors"
        >
          <DownloadIcon />
        </button>
        <button
          type="button"
          onClick={onOpenSettings}
          title="Settings"
          aria-label="Settings"
          className="flex items-center justify-center w-7 h-7 rounded-full bg-[var(--bg-overlay)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] transition-colors text-xs font-medium border border-[var(--border-subtle)]"
          style={{ width: '28px', height: '28px' }}
        >
          MA
        </button>
      </div>
    </aside>
  );
}
