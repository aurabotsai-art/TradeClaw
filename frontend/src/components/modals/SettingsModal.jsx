import React, { useState } from 'react';

const TAB_CAPITAL = 'Capital & Risk';
const TAB_API = 'API Keys';
const TAB_NOTIFICATIONS = 'Notifications';
const TAB_APPEARANCE = 'Appearance';

const TABS = [TAB_CAPITAL, TAB_API, TAB_NOTIFICATIONS, TAB_APPEARANCE];

export default function SettingsModal({
  isOpen,
  onClose,
  initialValues = {},
  onSave,
}) {
  const [activeTab, setActiveTab] = useState(TAB_CAPITAL);
  const [form, setForm] = useState({
    // Capital & Risk
    startingCapital: initialValues.startingCapital ?? 10000,
    dailyDdLimitPct: initialValues.dailyDdLimitPct ?? 1.5,
    perTradeRiskPct: initialValues.perTradeRiskPct ?? 1.0,
    atrMultiplier: initialValues.atrMultiplier ?? 2.0,
    kellyFraction: initialValues.kellyFraction ?? 0.5,
    // API Keys
    geminiApiKey: initialValues.geminiApiKey ?? '',
    apcaApiKeyId: initialValues.apcaApiKeyId ?? '',
    apcaApiSecretKey: initialValues.apcaApiSecretKey ?? '',
    binanceApiKey: initialValues.binanceApiKey ?? '',
    binanceApiSecret: initialValues.binanceApiSecret ?? '',
    polygonApiKey: initialValues.polygonApiKey ?? '',
    fmpApiKey: initialValues.fmpApiKey ?? '',
    // Notifications
    telegramBotToken: initialValues.telegramBotToken ?? '',
    telegramChatId: initialValues.telegramChatId ?? '',
    alertDdPct: initialValues.alertDdPct ?? 1.5,
    alertOnTrade: initialValues.alertOnTrade ?? true,
    alertOnCircuitBreaker: initialValues.alertOnCircuitBreaker ?? true,
    // Appearance
    accentColor: initialValues.accentColor ?? '#ff7a1a', // TradeClaw orange
    fontSize: initialValues.fontSize ?? 14,
    compactMode: initialValues.compactMode ?? false,
  });

  const [showSecrets, setShowSecrets] = useState(false);

  if (!isOpen) return null;

  const handleChange = (field) => (e) => {
    const value =
      e.target.type === 'checkbox'
        ? e.target.checked
        : e.target.type === 'number'
        ? e.target.valueAsNumber
        : e.target.value;
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    onSave?.(form);
    onClose?.();
  };

  const renderCapitalTab = () => (
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
          Starting capital (USD)
        </label>
        <input
          type="number"
          min={0}
          value={form.startingCapital}
          onChange={handleChange('startingCapital')}
          className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
            Daily DD limit (%)
          </label>
          <input
            type="number"
            min={0}
            step={0.1}
            value={form.dailyDdLimitPct}
            onChange={handleChange('dailyDdLimitPct')}
            className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
            Per trade risk (%)
          </label>
          <input
            type="number"
            min={0}
            step={0.1}
            value={form.perTradeRiskPct}
            onChange={handleChange('perTradeRiskPct')}
            className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
            ATR stop multiplier
          </label>
          <input
            type="number"
            min={0}
            step={0.1}
            value={form.atrMultiplier}
            onChange={handleChange('atrMultiplier')}
            className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
            Kelly fraction
          </label>
          <input
            type="number"
            min={0}
            max={1}
            step={0.05}
            value={form.kellyFraction}
            onChange={handleChange('kellyFraction')}
            className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          />
        </div>
      </div>
    </div>
  );

  const renderSecretInput = (label, field, placeholder) => (
    <div>
      <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
        {label}
      </label>
      <input
        type={showSecrets ? 'text' : 'password'}
        value={form[field]}
        onChange={handleChange(field)}
        placeholder={placeholder}
        className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
      />
    </div>
  );

  const renderApiTab = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs text-[var(--text-secondary)]">
          API keys are masked by default. They are sent securely to the backend over HTTPS.
        </span>
        <button
          type="button"
          onClick={() => setShowSecrets((v) => !v)}
          className="text-xs text-[var(--accent)] hover:underline"
        >
          {showSecrets ? 'Hide' : 'Show'} keys
        </button>
      </div>
      {renderSecretInput('Gemini API Key', 'geminiApiKey', 'GEMINI_API_KEY')}
      <div className="grid grid-cols-2 gap-3">
        {renderSecretInput('Alpaca API Key ID', 'apcaApiKeyId', 'APCA_API_KEY_ID')}
        {renderSecretInput('Alpaca Secret Key', 'apcaApiSecretKey', 'APCA_API_SECRET_KEY')}
      </div>
      <div className="grid grid-cols-2 gap-3">
        {renderSecretInput('Binance API Key', 'binanceApiKey', 'BINANCE_API_KEY')}
        {renderSecretInput('Binance Secret', 'binanceApiSecret', 'BINANCE_API_SECRET')}
      </div>
      {renderSecretInput('Polygon API Key', 'polygonApiKey', 'POLYGON_API_KEY')}
      {renderSecretInput('FMP API Key', 'fmpApiKey', 'FMP_API_KEY')}
    </div>
  );

  const renderNotificationsTab = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
            Telegram Bot Token
          </label>
          <input
            type={showSecrets ? 'text' : 'password'}
            value={form.telegramBotToken}
            onChange={handleChange('telegramBotToken')}
            placeholder="TELEGRAM_BOT_TOKEN"
            className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
            Telegram Chat ID
          </label>
          <input
            type="text"
            value={form.telegramChatId}
            onChange={handleChange('telegramChatId')}
            placeholder="@your_channel_or_id"
            className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
          Alert on daily drawdown ≥ (%)
        </label>
        <input
          type="number"
          min={0}
          step={0.1}
          value={form.alertDdPct}
          onChange={handleChange('alertDdPct')}
          className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
        />
      </div>

      <div className="space-y-2">
        <label className="flex items-center gap-2 text-xs text-[var(--text-primary)]">
          <input
            type="checkbox"
            checked={form.alertOnTrade}
            onChange={handleChange('alertOnTrade')}
            className="rounded border-[var(--border-subtle)]"
          />
          Alert when a trade is executed
        </label>
        <label className="flex items-center gap-2 text-xs text-[var(--text-primary)]">
          <input
            type="checkbox"
            checked={form.alertOnCircuitBreaker}
            onChange={handleChange('alertOnCircuitBreaker')}
            className="rounded border-[var(--border-subtle)]"
          />
          Alert when circuit breaker fires
        </label>
      </div>
    </div>
  );

  const renderAppearanceTab = () => (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
            Accent color
          </label>
          <input
            type="color"
            value={form.accentColor}
            onChange={handleChange('accentColor')}
            className="h-9 w-16 rounded cursor-pointer border border-[var(--border-subtle)] bg-[var(--bg-elevated)]"
          />
        </div>
        <div className="flex-1">
          <label className="block text-xs font-medium text-[var(--text-secondary)] mb-1">
            Font size (px)
          </label>
          <input
            type="number"
            min={12}
            max={18}
            value={form.fontSize}
            onChange={handleChange('fontSize')}
            className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          />
        </div>
      </div>
      <div>
        <label className="flex items-center gap-2 text-xs text-[var(--text-primary)]">
          <input
            type="checkbox"
            checked={form.compactMode}
            onChange={handleChange('compactMode')}
            className="rounded border-[var(--border-subtle)]"
          />
          Compact mode (denser chat and tables)
        </label>
        <p className="mt-1 text-[10px] text-[var(--text-muted)]">
          Useful when monitoring many symbols or running on smaller displays.
        </p>
      </div>
    </div>
  );

  const renderActiveTab = () => {
    switch (activeTab) {
      case TAB_CAPITAL:
        return renderCapitalTab();
      case TAB_API:
        return renderApiTab();
      case TAB_NOTIFICATIONS:
        return renderNotificationsTab();
      case TAB_APPEARANCE:
        return renderAppearanceTab();
      default:
        return null;
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-modal-title"
    >
      <div className="w-full max-w-3xl rounded-2xl bg-[var(--bg-raised)] border border-[var(--border-default)] shadow-2xl p-6 flex flex-col max-h-[80vh]">
        <div className="flex items-center justify-between mb-4">
          <h2
            id="settings-modal-title"
            className="text-lg font-semibold text-[var(--text-primary)]"
          >
            Settings
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-sm"
          >
            Esc
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-4 border-b border-[var(--border-subtle)]">
          {TABS.map((tab) => {
            const active = tab === activeTab;
            return (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-2 text-xs font-medium rounded-t-lg border-b-2 ${
                  active
                    ? 'border-[var(--accent)] text-[var(--text-primary)]'
                    : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-subtle)]'
                }`}
              >
                {tab}
              </button>
            );
          })}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto pr-1">{renderActiveTab()}</div>

        {/* Footer */}
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 text-sm rounded-lg border border-[var(--border-subtle)] text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="px-3 py-1.5 text-sm rounded-lg bg-[var(--accent)] text-white hover:bg-[var(--accent-strong)] transition-colors"
          >
            Save changes
          </button>
        </div>
      </div>
    </div>
  );
}

