/**
 * UI-3.3 SSE Streaming Hook — connects to /api/chat/stream, updates messages from token/tool events.
 * Wire actionLogStore, agentStore, tradingStore, toast when those exist.
 */
import { useState } from 'react';

// Stubs until Computer panel / trading / toast stores exist
const actionLogStore = {
  add: () => {},
  update: () => {},
};
const agentStore = {
  update: () => {},
};
const tradingStore = {
  addTrade: () => {},
};
const toast = {
  success: () => {},
};

export function useSSEStream() {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const send = async (sessionId, userMessage) => {
    setIsStreaming(true);

    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);

    const botMsgId = Date.now();
    setMessages((prev) => [...prev, { role: 'bot', id: botMsgId, content: '', toolCalls: [] }]);

    const url = `/api/chat/stream/${sessionId}?message=${encodeURIComponent(userMessage)}`;
    const eventSource = new EventSource(url);

    eventSource.onmessage = (e) => {
      let event;
      try {
        event = JSON.parse(e.data);
      } catch (err) {
        return;
      }

      if (event.type === 'token') {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === botMsgId ? { ...msg, content: msg.content + (event.content || '') } : msg
          )
        );
      }

      if (event.type === 'tool_start') {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === botMsgId
              ? {
                  ...msg,
                  toolCalls: [
                    ...(msg.toolCalls || []),
                    { name: event.name, args: event.args, status: 'running' },
                  ],
                }
              : msg
          )
        );
        actionLogStore.add(event);
      }

      if (event.type === 'tool_result') {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === botMsgId
              ? {
                  ...msg,
                  toolCalls: (msg.toolCalls || []).map((tc) =>
                    tc.name === event.name
                      ? { ...tc, status: 'done', result: event.data }
                      : tc
                  ),
                }
              : msg
          )
        );
        actionLogStore.update(event);
      }

      if (event.type === 'agent_result') {
        agentStore.update(event);
      }

      if (event.type === 'trade_result') {
        tradingStore.addTrade(event.data);
        toast.success(
          `Trade executed: ${event.data?.side} ${event.data?.qty} ${event.data?.symbol}`
        );
      }

      if (event.type === 'done') {
        setIsStreaming(false);
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      setIsStreaming(false);
      eventSource.close();
    };
  };

  return { messages, isStreaming, send };
}
