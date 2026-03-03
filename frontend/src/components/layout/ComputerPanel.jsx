/**
 * Right panel — toggleable (AI Computer / tools output).
 * Visibility controlled by parent; content TBD per plan.
 */
import React from 'react';

export default function ComputerPanel({ isOpen = false }) {
  if (!isOpen) return null;

  return (
    <aside
      className="w-80 flex-shrink-0 border-l border-[var(--border-subtle)] bg-[var(--bg-raised)] flex flex-col"
      aria-label="Computer panel"
    >
      <div className="p-3 border-b border-[var(--border-subtle)]">
        <h2 className="text-sm font-medium text-[var(--text-primary)]">Computer</h2>
      </div>
      <div className="flex-1 overflow-auto p-3 text-sm text-[var(--text-secondary)]">
        Tools and outputs appear here when Computer is on.
      </div>
    </aside>
  );
}
