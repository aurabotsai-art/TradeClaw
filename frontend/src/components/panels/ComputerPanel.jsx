import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useSettingsStore } from '../../stores/settingsStore';
import { useWebSocketState } from '../../hooks/useWebSocketState';
import ActionLogTab from './ActionLogTab';
import RiskTab from './RiskTab';

const PANEL_TABS = ['Status', 'Agents', 'Log', 'Risk', 'Positions', 'News'];

function PanelHeader() {
  return (
    <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border-subtle)]">
      <div className="text-xs font-medium text-[var(--text-primary)]">Computer</div>
    </div>
  );
}

function PanelTabs({ tabs, active, onSelect }) {
  return (
    <div className="flex px-2 py-1 gap-1 border-b border-[var(--border-subtle)] text-xs">
      {tabs.map((tab) => {
        const isActive = tab === active;
        return (
          <button
            key={tab}
            type="button"
            onClick={() => onSelect(tab)}
            className={`px-2 py-1 rounded-md ${
              isActive
                ? 'bg-[var(--bg-overlay)] text-[var(--text-primary)]'
                : 'text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]'
            }`}
          >
            {tab}
          </button>
        );
      })}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="mb-3">
      <h3 className="text-[11px] font-semibold text-[var(--text-secondary)] mb-1 uppercase tracking-wide">
        {title}
      </h3>
      {children}
    </section>
  );
}

function StatRow({ label, value, color }) {
  const cls =
    color === 'accent'
      ? 'text-[var(--accent)]'
      : color === 'green'
      ? 'text-tc-green'
      : 'text-[var(--text-primary)]';
  return (
    <div className="flex items-center justify-between text-[11px]">
      <span className="font-mono text-[var(--text-muted)]">{label}</span>
      <span className={`font-mono ${cls}`}>{value}</span>
    </div>
  );
}

function CircuitBreakerBadge({ fired, current_pct, limit_pct }) {
  const active = fired || (current_pct ?? 0) >= (limit_pct ?? 0);
  return (
    <div
      className={`px-3 py-2 rounded-xl text-xs font-mono ${
        active
          ? 'bg-red-500/10 border border-red-500/30 text-tc-red'
          : 'bg-[var(--bg-overlay)] border border-[var(--border-subtle)] text-[var(--text-secondary)]'
      }`}
    >
      <div className="flex items-center justify-between">
        <span>Circuit Breaker</span>
        <span>{active ? '🔴 FIRED' : 'OK'}</span>
      </div>
      <div className="mt-1 text-[10px]">
        DD {current_pct?.toFixed?.(2) ?? current_pct ?? 0}% / limit {limit_pct}%
      </div>
    </div>
  );
}

function MiniSparkline({ data }) {
  if (!data || !data.length) {
    return (
      <div className="h-8 rounded bg-[var(--bg-raised)] text-[10px] flex items-center justify-center text-[var(--text-muted)] mt-1">
        No data
      </div>
    );
  }
  return (
    <div className="h-8 rounded bg-[var(--bg-raised)] mt-1" aria-hidden>
      {/* Placeholder sparkline area */}
    </div>
  );
}

function PriceDisplay({ symbol, price, change }) {
  if (!symbol) {
    return <div className="text-xs text-[var(--text-muted)]">No active symbol</div>;
  }
  const up = typeof change === 'number' && change >= 0;
  const cls = up ? 'text-tc-green' : 'text-tc-red';
  return (
    <div className="flex items-baseline gap-2 text-xs">
      <span className="font-mono text-[var(--text-primary)]">{symbol}</span>
      <span className="font-mono text-[var(--text-secondary)]">
        {price != null ? `$${price}` : '-'}
      </span>
      <span className={`font-mono ${cls}`}>
        {change != null ? `${change.toFixed?.(2) ?? change}%` : ''}
      </span>
    </div>
  );
}

function NewsFeed() {
  return (
    <div className="text-[11px] text-[var(--text-secondary)]">
      Live news placeholder (wire /api/news later).
    </div>
  );
}

function StatusTab() {
  const state = useWebSocketState('/ws/state');
  const prices = useWebSocketState('/ws/prices');
  const activeSymbol = state.active_symbol || '';
  const activePrice = activeSymbol ? prices[activeSymbol] : null;

  return (
    <div className="flex flex-col gap-3 text-xs text-[var(--text-secondary)]">
      <Section title="System Status">
        <StatRow label="MODE" value={(state.mode || 'analysis').toUpperCase()} color="accent" />
        <StatRow
          label="TRADING_ENABLED"
          value={state.trading_enabled ? 'true' : 'false'}
        />
        <StatRow label="KILL_SWITCH" value={state.kill_switch ? '🔴 ON' : 'OFF'} />
        <StatRow label="UPTIME" value={state.uptime || '0s'} />
        <StatRow
          label="WS_STREAMS"
          value={`${state.streams_ok ?? 0}/3 OK`}
          color="green"
        />
      </Section>

      <CircuitBreakerBadge
        fired={state.cb_fired}
        current_pct={state.dd_pct ?? 0}
        limit_pct={1.5}
      />

      <Section title="Active Symbol">
        <PriceDisplay
          symbol={activeSymbol}
          price={activePrice?.price}
          change={activePrice?.change_pct}
        />
        <MiniSparkline data={activePrice?.history} />
      </Section>

      <Section title="Live News">
        <NewsFeed symbol={activeSymbol} limit={3} />
      </Section>
    </div>
  );
}

function AgentsTab() {
  return <div className="text-xs text-[var(--text-secondary)]">Agents tab placeholder.</div>;
}

function PositionsTab() {
  return <div className="text-xs text-[var(--text-secondary)]">Positions tab placeholder.</div>;
}

function NewsTab() {
  return <div className="text-xs text-[var(--text-secondary)]">News tab placeholder.</div>;
}

export default function ComputerPanel() {
  const panelOpen = useSettingsStore((s) => s.panelOpen);
  const [activeTab, setActiveTab] = useState('Status');

  return (
    <AnimatePresence>
      {panelOpen && (
        <motion.div
          className="computer-panel w-[340px] border-l border-[var(--border-subtle)] bg-[var(--bg-raised)] flex flex-col h-full"
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 340, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        >
          <PanelHeader />
          <PanelTabs tabs={PANEL_TABS} active={activeTab} onSelect={setActiveTab} />
          <div className="panel-body flex-1 overflow-y-auto p-3">
            {activeTab === 'Status' && <StatusTab />}
            {activeTab === 'Agents' && <AgentsTab />}
            {activeTab === 'Log' && <ActionLogTab />}
            {activeTab === 'Risk' && <RiskTab />}
            {activeTab === 'Positions' && <PositionsTab />}
            {activeTab === 'News' && <NewsTab />}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

