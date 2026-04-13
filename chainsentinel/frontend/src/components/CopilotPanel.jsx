import React, { useState, useRef, useEffect } from 'react';
import './CopilotPanel.css';

const QUICK_BUTTONS = [
  { label: 'What signals fired?', action: 'explain_signals' },
  { label: 'Trace fund flow', action: 'trace_funds' },
  { label: 'Known pattern?', action: 'pattern_match' },
  { label: 'Generate report', action: 'generate_report' },
  { label: "What's in ES?", action: 'es_summary' },
];

export function CopilotPanel({
  state = 'idle',
  messages = [],
  onSendMessage,
  onQuickAction,
  streaming = false,
  streamContent = '',
}) {
  const [input, setInput] = useState('');
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamContent]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    onSendMessage(trimmed);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="copilot">
      <div className="copilot__header">
        <h3>Copilot</h3>
        <span className={`badge badge--${state === 'idle' ? 'low' : state === 'watching' ? 'high' : 'med'}`}>
          {state}
        </span>
      </div>

      <div className="copilot__chat">
        {state === 'idle' && messages.length === 0 && (
          <div className="copilot__greeting">
            <p>ChainSentinel Copilot ready.</p>
            <p>Run an analysis to begin, or ask a question about a previous investigation.</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`copilot__msg copilot__msg--${msg.role}`}>
            <div className="copilot__msg-content">{msg.content}</div>
          </div>
        ))}

        {streaming && streamContent && (
          <div className="copilot__msg copilot__msg--assistant">
            <div className="copilot__msg-content copilot__msg-content--streaming">
              {streamContent}
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Quick Buttons */}
      {state === 'ready' && (
        <div className="copilot__quick">
          {QUICK_BUTTONS.map((btn) => (
            <button
              key={btn.action}
              className="btn-pill btn-pill--secondary copilot__quick-btn"
              onClick={() => onQuickAction(btn.action)}
            >
              {btn.label}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="copilot__input-row">
        <textarea
          className="copilot__input"
          placeholder="Ask about the investigation..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          disabled={streaming}
        />
        <button
          className="btn-pill btn-pill--primary copilot__send"
          onClick={handleSend}
          disabled={streaming || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}
