import React, { useState } from 'react';
import WelcomeScreen from '../components/chat/WelcomeScreen';
import InputBox from '../components/layout/InputBox';
import { useSSEStream } from '../hooks/useSSEStream';

export default function ChatView() {
  const [sessionId, setSessionId] = useState(null);
  const [input, setInput] = useState('');
  const { messages, isStreaming, send } = useSSEStream();

  const ensureSession = async () => {
    if (sessionId) return sessionId;
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'analysis' }),
    });
    const json = await res.json();
    const id = json.session_id;
    setSessionId(id);
    return id;
  };

  const handleSend = async (text) => {
    const content = (text ?? input).trim();
    if (!content || isStreaming) return;
    const id = await ensureSession();
    await send(id, content);
    setInput('');
  };

  return (
    <div className="flex flex-col h-full">
      {!sessionId && (
        <div className="flex-1">
          <WelcomeScreen
            onQuickAction={(label) => handleSend(label)}
            onSendInput={handleSend}
            onGoLive={() => console.log('Go Live')}
          />
        </div>
      )}
      {sessionId && (
        <div className="flex-1 overflow-auto p-4 text-[var(--text-secondary)]">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`mb-2 ${m.role === 'user' ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}`}
            >
              <strong className="mr-1">{m.role === 'user' ? 'You:' : 'Bot:'}</strong>
              <span>{m.content}</span>
            </div>
          ))}
        </div>
      )}
      <div className="flex items-center justify-center py-4 border-t border-[var(--border-subtle)]">
        <InputBox
          value={input}
          onChange={setInput}
          onSend={() => handleSend()}
          placeholder="Ask TradeClaw anything about markets, risk, or trades…"
        />
      </div>
    </div>
  );
}
