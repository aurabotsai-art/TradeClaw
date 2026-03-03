/**
 * UI-0.3 Exact Claude Top Bar
 * Height: 52px | Minimal: center context when in session, right = stars + avatar
 */
import React, { useState } from 'react';

const ICON_CLASS = 'w-5 h-5';

const ChevronDownIcon = () => (
  <svg className={ICON_CLASS} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
  </svg>
);
const StarIcon = () => (
  <svg className={ICON_CLASS} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
  </svg>
);
const ComputerIcon = () => (
  <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
  </svg>
);

const MODES = ['Paper', 'Analysis', 'Live'];

export default function TopBar({
  isSessionActive = false,
  chatTitle = '',
  modelLabel = 'gemini-1.5-pro',
  mode = 'Paper',
  computerOn = false,
  onModelSelect,
  onModeSelect,
  onComputerToggle,
  onStarsClick,
  onAvatarClick,
}) {
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [modeDropdownOpen, setModeDropdownOpen] = useState(false);

  return (
    <header
      className="flex items-center justify-between flex-shrink-0 border-b border-[var(--border-subtle)] bg-[var(--bg-raised)] px-4"
      style={{ height: '52px' }}
      role="banner"
    >
      {/* Left: empty (sidebar handles nav) */}
      <div className="w-12 flex-shrink-0" aria-hidden="true" />

      {/* Center: empty on home; in session: model dropdown + mode pill + computer toggle */}
      <div className="flex-1 flex items-center justify-center gap-3 min-w-0">
        {isSessionActive ? (
          <>
            {/* Model selector */}
            <div className="relative">
              <button
                type="button"
                onClick={() => { setModelDropdownOpen((v) => !v); setModeDropdownOpen(false); }}
                className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-sm text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
                aria-haspopup="listbox"
                aria-expanded={modelDropdownOpen}
              >
                <span>{modelLabel}</span>
                <ChevronDownIcon />
              </button>
              {modelDropdownOpen && (
                <div
                  className="absolute left-0 top-full mt-1 py-1 rounded-lg bg-[var(--bg-overlay)] border border-[var(--border-default)] shadow-lg z-50 min-w-[180px]"
                  role="listbox"
                >
                  <button
                    type="button"
                    role="option"
                    className="w-full text-left px-3 py-2 text-sm text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
                    onClick={() => { onModelSelect?.('gemini-1.5-pro'); setModelDropdownOpen(false); }}
                  >
                    gemini-1.5-pro
                  </button>
                  <button
                    type="button"
                    role="option"
                    className="w-full text-left px-3 py-2 text-sm text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
                    onClick={() => { onModelSelect?.('gemini-1.5-flash'); setModelDropdownOpen(false); }}
                  >
                    gemini-1.5-flash
                  </button>
                </div>
              )}
            </div>

            {/* Mode pill */}
            <div className="relative">
              <button
                type="button"
                onClick={() => { setModeDropdownOpen((v) => !v); setModelDropdownOpen(false); }}
                className="flex items-center gap-1 rounded-full px-3 py-1.5 text-sm bg-[var(--bg-overlay)] border border-[var(--border-subtle)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
              >
                {mode}
                {mode === 'Live' && ' 🔒'}
                <ChevronDownIcon />
              </button>
              {modeDropdownOpen && (
                <div
                  className="absolute left-1/2 -translate-x-1/2 top-full mt-1 py-1 rounded-lg bg-[var(--bg-overlay)] border border-[var(--border-default)] shadow-lg z-50 min-w-[120px]"
                  role="listbox"
                >
                  {MODES.map((m) => (
                    <button
                      key={m}
                      type="button"
                      role="option"
                      className="w-full text-left px-3 py-2 text-sm text-[var(--text-primary)] hover:bg-[var(--bg-hover)] flex items-center justify-between"
                      onClick={() => { onModeSelect?.(m); setModeDropdownOpen(false); }}
                    >
                      {m}
                      {m === 'Live' && ' 🔒'}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Computer toggle */}
            <button
              type="button"
              onClick={onComputerToggle}
              title={computerOn ? 'Computer on' : 'Computer off'}
              aria-label={computerOn ? 'Computer on' : 'Computer off'}
              className={`flex items-center justify-center w-9 h-9 rounded-lg transition-colors ${computerOn ? 'bg-[var(--accent-glow)] text-[var(--accent)]' : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]'}`}
            >
              <ComputerIcon />
            </button>
          </>
        ) : (
          chatTitle ? (
            <span className="text-sm text-[var(--text-primary)] truncate max-w-md" title={chatTitle}>
              {chatTitle}
            </span>
          ) : null
        )}
      </div>

      {/* Right: Stars + Avatar */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          type="button"
          onClick={onStarsClick}
          title="Upgrade / Favorites"
          aria-label="Upgrade"
          className="flex items-center justify-center w-9 h-9 rounded-lg text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] transition-colors"
        >
          <StarIcon />
        </button>
        <button
          type="button"
          onClick={onAvatarClick}
          title="Account"
          aria-label="Account"
          className="flex items-center justify-center w-8 h-8 rounded-full bg-[var(--bg-overlay)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] transition-colors text-xs font-medium border border-[var(--border-subtle)]"
        >
          MA
        </button>
      </div>
    </header>
  );
}
