/**
 * UI-3.4 Message Bubble Components — Claude style: user bubble, bot message with tool blocks
 */
import React from 'react';
import ToolCallBlock from './ToolCallBlock';
import AgentVerdictCards from './AgentVerdictCards';
import TradeCard from './TradeCard';

// ── User (right-aligned bubble) ────────────────────────────────────────────

export function UserBubble({ content }) {
  return (
    <div className="flex justify-end mb-6">
      <div
        className="max-w-[70%] rounded-2xl rounded-tr-md px-4 py-3 text-sm border"
        style={{
          background: 'var(--bg-overlay)',
          borderColor: 'var(--border-default)',
          color: 'var(--text-primary)',
        }}
      >
        {content}
      </div>
    </div>
  );
}

// ── Blinking cursor (streaming) ────────────────────────────────────────────

function BlinkingCursor() {
  return (
    <span
      className="inline-block w-2 h-4 ml-0.5 align-middle animate-pulse"
      style={{ background: 'var(--accent)' }}
      aria-hidden
    />
  );
}

// ── Simple markdown-style renderer (newlines, no full MD lib) ────────────────

function MarkdownRenderer({ content }) {
  if (!content) return null;
  return (
    <div className="whitespace-pre-wrap break-words text-[var(--text-primary)]">
      {content}
    </div>
  );
}

// Stubs: wire when trade result detection exists
// ── Bot message (avatar, tool blocks, text, meta) ────────────────────────────

export function BotMessage({
  content = '',
  toolCalls = [],
  agentResults = [],
  trade,
  isStreaming = false,
  timestamp,
  model,
}) {
  const ts =
    timestamp ?? new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const modelLabel = model ?? 'TradeClaw';

  return (
    <div className="flex gap-4 mb-6 max-w-[760px]">
      <div
        className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-lg"
        style={{ background: 'var(--bg-overlay)', border: '1px solid var(--border-subtle)' }}
        aria-hidden
      >
        🦾
      </div>
      <div className="flex-1 flex flex-col gap-3 min-w-0">
        {Array.isArray(toolCalls) &&
          toolCalls.length > 0 &&
          toolCalls.map((tc, i) => (
            <ToolCallBlock key={tc.name + String(i)} toolCall={tc} />
          ))}

        {Array.isArray(agentResults) && agentResults.length > 0 && (
          <AgentVerdictCards results={agentResults} />
        )}

        <div className="text-sm leading-relaxed">
          <MarkdownRenderer content={content} />
          {isStreaming && <BlinkingCursor />}
        </div>

        {trade && <TradeCard trade={trade} />}

        <div className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
          {ts} · {modelLabel}
        </div>
      </div>
    </div>
  );
}

