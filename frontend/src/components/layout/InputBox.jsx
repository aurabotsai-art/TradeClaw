/**
 * UI-0.5 Exact Claude Input Box
 * border-radius 16px, bg #2a2a2a, border #404040
 * Auto-grow textarea, [+] left, Model dropdown + audio/arrow right. Focus glow.
 */
import React, { useState, useRef, useEffect } from 'react';

const PlusIcon = ({ size = 16 }) => (
  <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
  </svg>
);

const AudioBarsIcon = ({ size = 18 }) => (
  <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
  </svg>
);

const ArrowUpIcon = ({ size = 18 }) => (
  <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18" />
  </svg>
);

const ChevronDownIcon = ({ size = 14 }) => (
  <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
  </svg>
);

const MODELS = ['gemini-1.5-pro', 'gemini-1.5-flash'];

function ModelDropdown({ value, onChange, className = '' }) {
  const [open, setOpen] = useState(false);

  return (
    <div className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-0.5 rounded-lg px-2 py-1.5 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] transition-colors"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span>{value}</span>
        <ChevronDownIcon />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" aria-hidden="true" onClick={() => setOpen(false)} />
          <div
            className="absolute right-0 bottom-full mb-1 py-1 rounded-lg bg-[var(--bg-overlay)] border border-[var(--border-default)] shadow-lg z-50 min-w-[160px]"
            role="listbox"
          >
            {MODELS.map((id) => (
              <button
                key={id}
                type="button"
                role="option"
                className="w-full text-left px-3 py-2 text-sm text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
                onClick={() => { onChange?.(id); setOpen(false); }}
              >
                {id}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

const MIN_TEXTAREA_HEIGHT = 52;
const MAX_TEXTAREA_HEIGHT = 200;

export default function InputBox({
  value = '',
  onChange,
  onSend,
  onAttach,
  placeholder = 'Type / for commands',
  modelLabel = 'gemini-1.5-pro',
  onModelSelect,
  className = '',
}) {
  const [focused, setFocused] = useState(false);
  const textareaRef = useRef(null);

  const hasInput = value.trim().length > 0;

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    const h = Math.min(Math.max(el.scrollHeight, MIN_TEXTAREA_HEIGHT), MAX_TEXTAREA_HEIGHT);
    el.style.height = `${h}px`;
  }, [value]);

  const handleChange = (e) => {
    onChange?.(e.target.value);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend?.();
    }
  };

  const handleSend = () => {
    onSend?.();
  };

  return (
    <div
      className={`
        w-full max-w-[640px] rounded-[16px] bg-[var(--bg-overlay)] border transition-[border-color,box-shadow]
        ${focused ? 'border-[var(--text-muted)] shadow-[0_0_0_1px_var(--accent-glow)]' : 'border-[var(--border-default)]'}
        ${className}
      `}
      style={{ borderWidth: '1px', background: '#2a2a2a' }}
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={1}
        className="input-textarea w-full bg-transparent px-4 pt-3 pb-1 text-[var(--text-primary)] placeholder-[var(--text-muted)] resize-none focus:outline-none overflow-y-auto"
        style={{ minHeight: MIN_TEXTAREA_HEIGHT, maxHeight: MAX_TEXTAREA_HEIGHT }}
        aria-label="Message input"
      />
      <div className="input-bottom-row flex items-center justify-between px-2 pb-2 pt-0">
        <button
          type="button"
          onClick={onAttach}
          className="input-icon-btn flex items-center justify-center w-8 h-8 rounded-lg text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] transition-colors"
          aria-label="Attach"
        >
          <PlusIcon size={16} />
        </button>
        <div className="flex-1 min-w-2" />
        <div className="input-right-controls flex items-center gap-1">
          <ModelDropdown value={modelLabel} onChange={onModelSelect} />
          <button
            type="button"
            onClick={handleSend}
            className={`input-icon-btn send-btn flex items-center justify-center w-8 h-8 rounded-lg transition-colors ${
              hasInput
                ? 'text-[var(--accent)] hover:bg-[var(--accent-glow)]'
                : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]'
            }`}
            aria-label={hasInput ? 'Send' : 'Voice input'}
          >
            {hasInput ? <ArrowUpIcon size={18} /> : <AudioBarsIcon size={18} />}
          </button>
        </div>
      </div>
    </div>
  );
}
