import React, { useState } from 'react';
import { useQuery } from '../hooks/useQuery';

function Section({ title, children }) {
  return (
    <section className="mb-6">
      <h2 className="text-sm font-semibold text-[var(--text-secondary)] mb-2 uppercase tracking-wide">
        {title}
      </h2>
      {children}
    </section>
  );
}

function SymbolPickerModal({ open, onClose, onAdd }) {
  const [symbol, setSymbol] = useState('');
  const [assetClass, setAssetClass] = useState('equity');

  if (!open) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!symbol) return;
    await onAdd(symbol.toUpperCase(), assetClass);
    setSymbol('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-raised)] p-4 text-xs">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2">
          Add Symbol to Universe
        </h3>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex flex-col gap-1">
            <label className="font-mono text-[var(--text-muted)]">Symbol</label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="px-2 py-1 rounded-md bg-[var(--bg-base)] border border-[var(--border-subtle)] text-[var(--text-primary)] font-mono"
              autoFocus
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="font-mono text-[var(--text-muted)]">Asset Class</label>
            <select
              value={assetClass}
              onChange={(e) => setAssetClass(e.target.value)}
              className="px-2 py-1 rounded-md bg-[var(--bg-base)] border border-[var(--border-subtle)] text-[var(--text-primary)] font-mono"
            >
              <option value="equity">Equity</option>
              <option value="crypto">Crypto</option>
              <option value="fx">FX</option>
              <option value="futures">Futures</option>
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded-md border border-[var(--border-subtle)] text-[var(--text-secondary)] font-mono"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-3 py-1.5 rounded-md bg-[var(--accent)] text-white font-mono"
            >
              Add
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function UniverseView() {
  const { data: universeRes } = useQuery('/api/universe');
  const { data: candidatesRes } = useQuery('/api/universe/candidates');
  const { data: corrRes } = useQuery('/api/risk/correlation');

  const symbols = universeRes?.symbols || [];
  const candidates = candidatesRes?.candidates || [];
  const matrix = corrRes?.matrix || [];

  const [modalOpen, setModalOpen] = useState(false);

  const handleRemove = async (symbol) => {
    const ok = window.confirm(`Remove ${symbol} from universe?`);
    if (!ok) return;
    try {
      await fetch(`http://localhost:8000/api/universe/${encodeURIComponent(symbol)}`, {
        method: 'DELETE',
      });
    } catch {
      // ignore
    }
  };

  const handleAddSymbol = async (symbol, assetClass) => {
    try {
      await fetch('http://localhost:8000/api/universe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, asset_class: assetClass }),
      });
    } catch {
      // ignore
    } finally {
      setModalOpen(false);
    }
  };

  const universeSymbols = symbols.map((s) => s.symbol);

  return (
    <div className="p-6 text-[var(--text-primary)] space-y-6">
      <h1 className="font-display text-2xl font-semibold mb-1">Universe</h1>
      <p className="text-[var(--text-secondary)] mb-4">
        Current trading universe, scanner candidates, and correlation risk.
      </p>

      {/* 1. Universe table */}
      <Section title="Universe">
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3">
          <div className="flex items-center mb-2">
            <button
              type="button"
              onClick={() => setModalOpen(true)}
              className="ml-auto px-3 py-1.5 rounded-md bg-[var(--accent)] text-xs font-mono text-white hover:bg-[var(--accent-hover)]"
            >
              + Add Symbol
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                <tr>
                  <th className="text-left py-1 pr-3 font-normal">Symbol</th>
                  <th className="text-left py-1 pr-3 font-normal">Asset Class</th>
                  <th className="text-right py-1 pr-3 font-normal">Price</th>
                  <th className="text-right py-1 pr-3 font-normal">24h Change</th>
                  <th className="text-right py-1 pr-3 font-normal">Avg Volume</th>
                  <th className="text-right py-1 pr-3 font-normal">IC Score</th>
                  <th className="text-left py-1 pr-0 font-normal">Status</th>
                  <th className="text-right py-1 pr-0 font-normal">Actions</th>
                </tr>
              </thead>
              <tbody>
                {symbols.length === 0 ? (
                  <tr>
                    <td
                      colSpan={8}
                      className="py-2 text-center text-[var(--text-muted)] font-mono"
                    >
                      Universe is empty.
                    </td>
                  </tr>
                ) : (
                  symbols.map((s) => (
                    <tr
                      key={s.symbol}
                      className="border-b border-[var(--border-subtle)]"
                    >
                      <td className="py-1 pr-3">{s.symbol}</td>
                      <td className="py-1 pr-3 text-[var(--text-secondary)]">
                        {s.asset_class || '-'}
                      </td>
                      <td className="py-1 pr-3 text-right font-mono">-</td>
                      <td className="py-1 pr-3 text-right font-mono">-</td>
                      <td className="py-1 pr-3 text-right font-mono">-</td>
                      <td className="py-1 pr-3 text-right font-mono">-</td>
                      <td className="py-1 pr-0 text-[var(--text-secondary)]">Active</td>
                      <td className="py-1 pr-0 text-right">
                        <button
                          type="button"
                          onClick={() => handleRemove(s.symbol)}
                          className="px-2 py-1 rounded-md border border-[var(--border-subtle)] text-[10px] font-mono text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </Section>

      {/* 3. Universe scanner results */}
      <Section title="Scanner Candidates">
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3">
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="border-b border-[var(--border-subtle)] text-[var(--text-muted)]">
                <tr>
                  <th className="text-left py-1 pr-3 font-normal">Symbol</th>
                  <th className="text-right py-1 pr-3 font-normal">Score</th>
                  <th className="text-left py-1 pr-3 font-normal">Why Recommended</th>
                  <th className="text-right py-1 pr-0 font-normal">Actions</th>
                </tr>
              </thead>
              <tbody>
                {candidates.length === 0 ? (
                  <tr>
                    <td
                      colSpan={4}
                      className="py-2 text-center text-[var(--text-muted)] font-mono"
                    >
                      No scanner candidates yet.
                    </td>
                  </tr>
                ) : (
                  candidates.map((c) => (
                    <tr key={c.symbol} className="border-b border-[var(--border-subtle)]">
                      <td className="py-1 pr-3">{c.symbol}</td>
                      <td className="py-1 pr-3 text-right font-mono">{c.score}</td>
                      <td className="py-1 pr-3 text-[var(--text-secondary)]">
                        {c.why || ''}
                      </td>
                      <td className="py-1 pr-0 text-right">
                        <button
                          type="button"
                          disabled={universeSymbols.includes(c.symbol)}
                          onClick={() => handleAddSymbol(c.symbol, c.asset_class || 'equity')}
                          className="px-2 py-1 rounded-md border border-[var(--border-subtle)] text-[10px] font-mono text-[var(--text-secondary)] hover:bg-[var(--bg-hover)] disabled:opacity-50"
                        >
                          {universeSymbols.includes(c.symbol) ? 'Added' : 'Add'}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </Section>

      {/* 4. Correlation matrix heatmap */}
      <Section title="Correlation Matrix">
        <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-overlay)] p-3 overflow-auto text-[11px]">
          {matrix.length === 0 ? (
            <div className="text-[var(--text-muted)] font-mono">
              Correlation matrix placeholder (wire /api/risk/correlation to real data).
            </div>
          ) : (
            <table className="border-collapse">
              <thead>
                <tr>
                  <th className="p-1" />
                  {matrix[0].symbols.map((sym) => (
                    <th key={sym} className="p-1 text-center">
                      {sym}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.map((row) => (
                  <tr key={row.symbol}>
                    <td className="p-1 pr-2 text-right font-mono text-[var(--text-secondary)]">
                      {row.symbol}
                    </td>
                    {row.values.map((v, idx) => {
                      const val = v;
                      const intensity = Math.min(1, Math.abs(val));
                      const red = val > 0 ? Math.round(255 * intensity) : 0;
                      const blue = val < 0 ? Math.round(255 * intensity) : 0;
                      const bg = `rgba(${red},0,${blue},0.3)`;
                      return (
                        <td
                          key={idx}
                          className="w-6 h-6 text-center align-middle font-mono"
                          style={{ background: bg }}
                        >
                          {val.toFixed?.(2) ?? val}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Section>

      <SymbolPickerModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onAdd={handleAddSymbol}
      />
    </div>
  );
}

