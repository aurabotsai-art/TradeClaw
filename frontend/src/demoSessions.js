// Demo session data shared between ChatHistory and HistoryView.
// In real app this would come from backend / persistence.

export const DEMO_SESSIONS = [
  {
    id: '1',
    title: 'Analyze NVDA setup for today',
    firstMessage: 'Walk through NVDA technicals and today’s catalysts.',
    timestamp: Date.now() - 2 * 3600000,
    mode: 'Analysis',
    pnl: 125.4,
  },
  {
    id: '2',
    title: 'Run consensus on BTC/USD',
    firstMessage: 'Get multi‑agent consensus before entering BTC/USD.',
    timestamp: Date.now() - 5 * 3600000,
    mode: 'Paper',
    pnl: -42.75,
  },
  {
    id: '3',
    title: '2022 regime backtest results',
    firstMessage: 'Summarize regime shifts and factor performance in 2022.',
    timestamp: Date.now() - 86400000,
    mode: 'Analysis',
    pnl: 0,
  },
  {
    id: '4',
    title: 'Show open positions PnL',
    firstMessage: 'List all open positions and per‑symbol PnL.',
    timestamp: Date.now() - 86400000 - 3600000,
    mode: 'Live',
    pnl: 317.92,
  },
  {
    id: '5',
    title: 'Paper trade MSFT 1% risk',
    firstMessage: 'Size a paper MSFT trade with 1% of equity at risk.',
    timestamp: Date.now() - 3 * 86400000,
    mode: 'Paper',
    pnl: null,
  },
];

