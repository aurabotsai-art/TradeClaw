import React from 'react';

/**
 * UI-3.6 Agent Verdict Cards
 * Shows after a consensus run — 4 cards in a grid.
 */
export default function AgentVerdictCards({ results = [] }) {
  if (!results.length) return null;

  return (
    <div className="grid grid-cols-2 gap-2 my-2">
      {results.map((agent) => {
        const approve = agent.verdict === 'APPROVE';
        return (
          <div
            key={agent.name}
            className={`p-3 rounded-xl border text-xs ${
              approve
                ? 'border-green-500/30 bg-green-500/5'
                : 'border-red-500/30 bg-red-500/5'
            }`}
          >
            <div className="font-mono uppercase tracking-wide text-[10px]" style={{ color: 'var(--text-muted)' }}>
              {agent.name} · {agent.model}
            </div>
            <div
              className={`font-display font-bold text-sm mt-1 ${
                approve ? 'text-tc-green' : 'text-tc-red'
              }`}
            >
              {agent.verdict}
              {agent.score != null && agent.score !== '' && ` · ${agent.score}/10`}
            </div>
            <div
              className="mt-1 leading-relaxed"
              style={{ color: 'var(--text-secondary)' }}
            >
              {agent.reasoning}
            </div>
          </div>
        );
      })}
    </div>
  );
}

