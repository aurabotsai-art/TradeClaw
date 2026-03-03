import React from 'react';

/**
 * UI-6.2 Kill Switch Modal
 *
 * Props:
 * - open: boolean
 * - enabled: boolean (current kill switch state; true = ON / trading halted)
 * - onActivate: () => void    // called when activating kill switch
 * - onResume: () => void      // called when resuming trading
 * - onClosePositions?: () => void // optional handler for 'Close positions'
 * - onCancel: () => void
 */
export default function KillSwitchModal({
  open,
  enabled,
  onActivate,
  onResume,
  onClosePositions,
  onCancel,
}) {
  if (!open) return null;

  const handlePrimary = () => {
    if (enabled) {
      onResume?.();
    } else {
      onActivate?.();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-raised)] p-4 text-sm text-[var(--text-primary)]">
        {/* State A: Kill switch OFF (trading active) */}
        {!enabled && (
          <div className="space-y-3">
            <div className="text-base font-semibold flex items-center gap-2">
              <span aria-hidden>⚡</span>
              <span>Trading is currently ACTIVE</span>
            </div>
            <p className="text-[var(--text-secondary)]">
              Clicking below will immediately halt all trading. No new orders will be placed. Open
              positions will <span className="font-semibold">NOT</span> be closed.
            </p>
          </div>
        )}

        {/* State B: Kill switch ON (trading halted) */}
        {enabled && (
          <div className="space-y-3">
            <div className="text-base font-semibold flex items-center gap-2">
              <span aria-hidden>🔴</span>
              <span>Kill switch is ACTIVE — all trading halted</span>
            </div>
            <p className="text-[var(--text-secondary)]">
              You can optionally close open positions and then resume trading when ready.
            </p>
            {onClosePositions && (
              <button
                type="button"
                onClick={onClosePositions}
                className="inline-flex items-center px-3 py-1.5 rounded-md border border-[var(--border-subtle)] text-[11px] font-mono text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
              >
                Close positions
              </button>
            )}
          </div>
        )}

        <div className="mt-4 flex justify-end gap-2 text-xs font-mono">
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-1.5 rounded-md border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handlePrimary}
            className={`px-3 py-1.5 rounded-md text-white ${
              enabled
                ? 'bg-green-600 hover:bg-green-500'
                : 'bg-red-600 hover:bg-red-500'
            }`}
          >
            {enabled ? '✅ Resume Trading' : '🔴 Activate Kill Switch'}
          </button>
        </div>
      </div>
    </div>
  );
}

