import { useEffect, useRef, useState } from 'react';

const WS_BASE_URL =
  import.meta.env.VITE_WS_BASE_URL ||
  (() => {
    if (typeof window === 'undefined') return 'ws://localhost:8000';
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = window.location.hostname;
    const port = window.location.port || '8000';
    return `${protocol}://${host}:${port}`;
  })();

/**
 * useWebSocketState
 * - For `/ws/state`: keeps latest state object.
 * - For `/ws/prices`: keeps a map { [symbol]: { price, change_pct, history: [...] } }.
 * - Auto-reconnects 2s after close.
 */
export function useWebSocketState(endpoint) {
  const isState = endpoint.endsWith('/state');
  const isPrices = endpoint.endsWith('/prices');

  const [value, setValue] = useState(() =>
    isState
      ? {
          mode: 'analysis',
          trading_enabled: false,
          kill_switch: false,
          uptime: '0s',
          streams_ok: 0,
          cb_fired: false,
          dd_pct: 0,
          active_symbol: '',
          positions: [],
        }
      : {}
  );

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  useEffect(() => {
    const url = `${WS_BASE_URL}${endpoint}`;

    const connect = () => {
      try {
        wsRef.current = new WebSocket(url);
      } catch {
        return;
      }

      wsRef.current.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (isState) {
            setValue((prev) => ({ ...prev, ...payload }));
          } else if (isPrices) {
            // backend sends full map { symbol: { price, change_pct, ... } }
            setValue((prev) => {
              const next = { ...prev };
              Object.entries(payload || {}).forEach(([symbol, p]) => {
                const prevHist = prev[symbol]?.history || [];
                const price = p.price;
                const change_pct = p.change_pct;
                next[symbol] = {
                  ...p,
                  history: [...prevHist.slice(-49), { price, ts: Date.now() }],
                  change_pct,
                };
              });
              return next;
            });
          } else {
            setValue(payload);
          }
        } catch {
          // ignore bad frames
        }
      };

      wsRef.current.onclose = () => {
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 2000);
      };

      wsRef.current.onerror = () => {
        try {
          wsRef.current && wsRef.current.close();
        } catch {
          // ignore
        }
      };
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {
          // ignore
        }
      }
    };
  }, [endpoint, isState, isPrices]);

  return value;
}

