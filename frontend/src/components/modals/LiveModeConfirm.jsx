import React, { useState } from 'react';

const CONFIRM_PHRASE = 'I ACCEPT REAL MONEY RISK';

export default function LiveModeConfirm({
  isOpen,
  onClose,
  onLiveEnabled,
  dailyLossLimitUsd = 150,
  baseCapitalUsd = 10000,
}) {
  const [step, setStep] = useState(1);
  const [confirmText, setConfirmText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');

  if (!isOpen) {
    return null;
  }

  const resetState = () => {
    setStep(1);
    setConfirmText('');
    setIsSubmitting(false);
    setError('');
    setToast('');
  };

  const handleCancel = () => {
    resetState();
    onClose?.();
  };

  const handleContinue = () => {
    setStep(2);
    setError('');
  };

  const handleEnableLive = async () => {
    if (confirmText.trim() !== CONFIRM_PHRASE) {
      setError(`You must type the exact phrase: "${CONFIRM_PHRASE}"`);
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      // Backend is responsible for switching APCA_API_BASE_URL to live
      // and persisting any risk-mode flags.
      const res = await fetch('/api/risk/set-live-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ live: true }),
      });

      if (!res.ok) {
        throw new Error(`Backend responded with ${res.status}`);
      }

      setToast('Live mode active. Real money trades will now be routed.');
      onLiveEnabled?.();

      // Small delay so user can see success state before closing.
      setTimeout(() => {
        handleCancel();
      }, 900);
    } catch (e) {
      setError('Failed to enable live mode. Please try again or check server logs.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="live-mode-title"
    >
      <div className="w-full max-w-md rounded-2xl bg-[var(--bg-raised)] border border-[var(--border-default)] shadow-2xl p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2
            id="live-mode-title"
            className="text-lg font-semibold text-[var(--text-primary)] flex items-center gap-2"
          >
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-red-600/10 text-red-500 text-sm">
              !
            </span>
            Enable Live Trading
          </h2>
          <button
            type="button"
            onClick={handleCancel}
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-sm"
          >
            Esc
          </button>
        </div>

        {/* Body */}
        {step === 1 && (
          <div className="space-y-4">
            <div className="space-y-2">
              <p className="text-sm font-medium text-red-500">
                You are about to enable LIVE trading.
              </p>
              <p className="text-sm text-[var(--text-primary)]">
                Real money will be at risk. This bot will send orders to your connected broker.
              </p>
              <div className="mt-3 rounded-lg bg-[var(--bg-overlay)] border border-[var(--border-subtle)] px-3 py-2 text-sm">
                <p className="text-[var(--text-secondary)]">Configured capital: ${baseCapitalUsd.toLocaleString()}</p>
                <p className="text-[var(--text-secondary)]">
                  Daily loss limit:{' '}
                  <span className="font-semibold text-red-500">
                    ${dailyLossLimitUsd.toLocaleString()} ({((dailyLossLimitUsd / baseCapitalUsd) * 100).toFixed(1)}%)
                  </span>
                </p>
                <p className="mt-1 text-xs text-[var(--text-muted)]">
                  When the daily drawdown exceeds this limit, the circuit breaker will halt new trades and log a
                  post-mortem.
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={handleCancel}
                className="px-3 py-1.5 text-sm rounded-lg border border-[var(--border-subtle)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleContinue}
                className="px-3 py-1.5 text-sm rounded-lg bg-red-600 text-white hover:bg-red-500 transition-colors"
              >
                I understand, continue →
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <p className="text-sm text-[var(--text-primary)]">
              To enable live trading, please type the exact phrase below to confirm that you accept real-money risk.
            </p>
            <div className="space-y-2">
              <p className="text-xs font-mono text-[var(--text-secondary)] select-all">
                {CONFIRM_PHRASE}
              </p>
              <input
                type="text"
                autoFocus
                value={confirmText}
                onChange={(e) => { setConfirmText(e.target.value); setError(''); }}
                placeholder='Type "I ACCEPT REAL MONEY RISK"'
                className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
              />
            </div>

            {error && (
              <p className="text-xs text-red-500">
                {error}
              </p>
            )}
            {toast && (
              <p className="text-xs text-emerald-500">
                {toast}
              </p>
            )}

            <div className="flex justify-between items-center pt-2">
              <button
                type="button"
                onClick={handleCancel}
                className="px-3 py-1.5 text-sm rounded-lg border border-[var(--border-subtle)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleEnableLive}
                disabled={isSubmitting}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  isSubmitting
                    ? 'bg-[var(--bg-hover)] text-[var(--text-secondary)] cursor-wait'
                    : 'bg-emerald-600 text-white hover:bg-emerald-500'
                }`}
              >
                {isSubmitting ? 'Enabling…' : 'Enable Live Trading'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

