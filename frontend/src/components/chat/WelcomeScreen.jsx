/**
 * UI-0.4 Exact Claude Welcome / Home Screen
 * Plan pill, greeting, input box, quick action pills
 */
import React, { useState } from 'react';
import InputBox from '../layout/InputBox';

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Evening';
}

function Pill({ icon, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-2 rounded-full px-4 py-2.5 text-sm bg-[var(--bg-overlay)] border border-[var(--border-subtle)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)] hover:border-[var(--border-default)] transition-colors"
    >
      <span aria-hidden="true">{icon}</span>
      <span>{children}</span>
    </button>
  );
}

const QUICK_PILLS = [
  { icon: '🔍', label: 'Analyze' },
  { icon: '⚡', label: 'Trade' },
  { icon: '📊', label: 'PnL' },
  { icon: '🧪', label: 'Backtest' },
  { icon: '🐋', label: 'Whales' },
  { icon: '🌊', label: 'Regime' },
];

export default function WelcomeScreen({ userName = 'Muhammad', onQuickAction, onSendInput, onGoLive }) {
  const [inputValue, setInputValue] = useState('');

  const handleSend = () => {
    if (inputValue.trim()) {
      onSendInput?.(inputValue.trim());
      setInputValue('');
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 px-4 bg-[var(--bg-base)]">
      {/* Plan pill — top, same as Claude */}
      <div
        className="rounded-full px-4 py-2 text-sm bg-[var(--bg-overlay)] border border-[var(--border-subtle)] text-[var(--text-secondary)]"
        role="status"
      >
        Paper Mode ·{' '}
        <button
          type="button"
          onClick={onGoLive}
          className="text-[var(--accent)] hover:text-[var(--accent-hover)] cursor-pointer font-medium transition-colors"
        >
          Go Live →
        </button>
      </div>

      {/* Greeting — exact Claude style */}
      <h1
        className="text-4xl md:text-5xl font-display font-semibold text-center text-[var(--text-primary)] tracking-tight"
        style={{ fontFamily: 'var(--font-display)' }}
      >
        <span className="text-[var(--accent)]" aria-hidden="true">
          ✳
        </span>{' '}
        {getGreeting()}, {userName}
      </h1>

      {/* Input box — exact Claude dimensions and style */}
      <div className="w-full max-w-[640px]">
        <InputBox
          value={inputValue}
          onChange={setInputValue}
          onSend={handleSend}
          placeholder="Type / for commands"
        />
      </div>

      {/* Quick action pills — replaces Claude's Write/Learn/Code */}
      <div className="flex flex-wrap items-center justify-center gap-2">
        {QUICK_PILLS.map(({ icon, label }) => (
          <Pill
            key={label}
            icon={icon}
            onClick={() => onQuickAction?.(label)}
          >
            {label}
          </Pill>
        ))}
      </div>
    </div>
  );
}
