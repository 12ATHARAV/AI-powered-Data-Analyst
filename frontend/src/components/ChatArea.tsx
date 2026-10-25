import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Code, Copy, Check, ChevronDown, ChevronRight, AlertOctagon, Sparkles } from 'lucide-react';
import { ChartRenderer } from './ChartRenderer';
import type { ChartSpec } from './ChartRenderer';
import { MarkdownContent } from './MarkdownContent';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  sql?: string;
  pandas?: string;
  chartSpec?: ChartSpec;
  anomalies?: any[];
  reasoning?: string;
  modelUsed?: string;
  provider?: string;
}

interface ChatAreaProps {
  messages: ChatMessage[];
  onSendMessage: (query: string) => void;
  isLoading: boolean;
  onSelectPrompt: (prompt: string) => void;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  onSendMessage,
  isLoading,
  onSelectPrompt,
}) => {
  const [input, setInput] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [openReasoning, setOpenReasoning] = useState<{ [key: string]: boolean }>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const feedRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);

  useEffect(() => {
    if (stickToBottomRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  const handleFeedScroll = () => {
    const el = feedRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    stickToBottomRef.current = distanceFromBottom < 120;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const toggleReasoning = (msgId: string) => {
    setOpenReasoning((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      minHeight: 0,
      background: 'transparent',
    }}>
      {/* Message Feed */}
      <div
        ref={feedRef}
        onScroll={handleFeedScroll}
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
          padding: '24px 32px',
          display: 'flex',
          flexDirection: 'column',
          gap: '24px',
        }}
      >
        {messages.length === 0 ? (
          <div style={{
            margin: 'auto',
            maxWidth: '650px',
            textAlign: 'center',
            padding: '40px 24px',
            background: 'var(--bg-card)',
            borderRadius: '16px',
            border: '1px solid var(--border-subtle)',
          }}>
            <div style={{
              width: '54px',
              height: '54px',
              borderRadius: '16px',
              background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px auto',
              boxShadow: '0 8px 24px rgba(99, 102, 241, 0.4)',
            }}>
              <Sparkles size={28} color="#ffffff" />
            </div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '8px' }}>
              Welcome to your AI Data Analyst
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '24px', lineHeight: 1.6 }}>
              Ask questions in plain English, query across multiple CSV files, generate interactive charts, and diagnose statistical anomalies with automated causal reasoning.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', textAlign: 'left' }}>
              {[
                "Which region generated the highest revenue?",
                "Show monthly sales trends.",
                "Which products are underperforming?",
                "What are the top five customers?",
              ].map((p, i) => (
                <button
                  key={i}
                  onClick={() => onSelectPrompt(p)}
                  className="btn btn-secondary"
                  style={{ fontSize: '0.82rem', padding: '10px 14px', justifyContent: 'flex-start' }}
                >
                  <Bot size={14} color="#818cf8" />
                  <span>{p}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className="msg-enter"
              style={{
                display: 'flex',
                gap: '14px',
                alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: msg.sender === 'user' ? '70%' : '85%',
              }}
            >
              {/* Avatar */}
              <div style={{
                width: '34px',
                height: '34px',
                minWidth: '34px',
                borderRadius: '8px',
                background: msg.sender === 'user' ? 'rgba(255, 255, 255, 0.1)' : 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: msg.sender === 'assistant' ? '0 0 12px rgba(99, 102, 241, 0.4)' : 'none',
              }}>
                {msg.sender === 'user' ? <User size={18} /> : <Bot size={18} color="#ffffff" />}
              </div>

              {/* Bubble */}
              <div style={{
                background: msg.sender === 'user' ? 'rgba(99, 102, 241, 0.2)' : 'var(--bg-card)',
                border: `1px solid ${msg.sender === 'user' ? 'rgba(99, 102, 241, 0.4)' : 'var(--border-subtle)'}`,
                borderRadius: '12px',
                padding: '16px 20px',
                boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
                width: '100%',
              }}>
                {/* Header for Assistant */}
                {msg.sender === 'assistant' && msg.modelUsed && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                    <span style={{
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: '4px',
                      background: msg.provider === 'NVIDIA' ? 'rgba(99, 102, 241, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                      color: msg.provider === 'NVIDIA' ? '#818cf8' : '#fbbf24',
                      border: `1px solid ${msg.provider === 'NVIDIA' ? 'rgba(99, 102, 241, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
                    }}>
                      {msg.modelUsed}
                    </span>
                  </div>
                )}

                {/* Text Content */}
                {msg.sender === 'user' ? (
                  <div style={{
                    fontSize: '0.92rem',
                    lineHeight: 1.6,
                    color: 'var(--text-main)',
                    whiteSpace: 'pre-wrap',
                  }}>
                    {msg.content}
                  </div>
                ) : (
                  <MarkdownContent content={msg.content} />
                )}

                {/* Generated Chart */}
                {msg.chartSpec && <ChartRenderer spec={msg.chartSpec} />}

                {/* Generated SQL Code Block */}
                {msg.sql && (
                  <div className="reveal" style={{ marginTop: '14px' }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '6px 12px',
                      background: '#0d131f',
                      borderTopLeftRadius: '8px',
                      borderTopRightRadius: '8px',
                      border: '1px solid var(--border-subtle)',
                      borderBottom: 'none',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Code size={14} color="#67e8f9" />
                        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>
                          GENERATED SQL QUERY
                        </span>
                      </div>
                      <button
                        onClick={() => copyToClipboard(msg.sql!, `sql-${msg.id}`)}
                        className="btn btn-secondary"
                        style={{ padding: '2px 6px', fontSize: '0.7rem' }}
                      >
                        {copiedId === `sql-${msg.id}` ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                        <span>{copiedId === `sql-${msg.id}` ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                    <div className="code-box" style={{ padding: '12px', borderTopLeftRadius: 0, borderTopRightRadius: 0 }}>
                      <pre style={{ margin: 0, color: '#67e8f9', fontSize: '0.8rem' }}>{msg.sql}</pre>
                    </div>
                  </div>
                )}

                {/* Anomaly Alerts */}
                {msg.anomalies && msg.anomalies.length > 0 && (
                  <div style={{
                    marginTop: '14px',
                    padding: '12px 14px',
                    background: 'rgba(245, 158, 11, 0.08)',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    borderRadius: '8px',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <AlertOctagon size={16} color="#fbbf24" />
                      <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#fbbf24' }}>
                        Statistical Anomalies Detected ({msg.anomalies.length})
                      </span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {msg.anomalies.map((anom: any, idx: number) => (
                        <div key={idx} style={{ fontSize: '0.78rem', color: '#e2e8f0', lineHeight: 1.4 }}>
                          <strong>{anom.table_name}.{anom.column_name}:</strong> {anom.summary}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Reasoning Accordion */}
                {msg.reasoning && (
                  <div style={{ marginTop: '12px' }}>
                    <button
                      onClick={() => toggleReasoning(msg.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--text-dim)',
                        fontSize: '0.75rem',
                        cursor: 'pointer',
                        padding: '4px 0',
                      }}
                    >
                      {openReasoning[msg.id] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                      <span>Explain Reasoning Behind Response</span>
                    </button>
                    {openReasoning[msg.id] && (
                      <div className="reveal" style={{
                        marginTop: '6px',
                        padding: '10px 14px',
                        background: 'rgba(255, 255, 255, 0.02)',
                        borderLeft: '2px solid #818cf8',
                        borderRadius: '4px',
                        fontSize: '0.8rem',
                        color: 'var(--text-muted)',
                        whiteSpace: 'pre-wrap',
                      }}>
                        {msg.reasoning}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="msg-enter" style={{ display: 'flex', gap: '14px', alignSelf: 'flex-start' }}>
            <div style={{
              width: '34px',
              height: '34px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px rgba(99, 102, 241, 0.4)',
            }}>
              <Bot size={18} color="#ffffff" />
            </div>
            <div style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '12px',
              padding: '14px 20px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              fontSize: '0.85rem',
              color: 'var(--text-muted)',
            }}>
              <span className="typing-dots" aria-hidden="true">
                <span /><span /><span />
              </span>
              <span>Agents are analyzing your data — watch the Active Logs drawer for live traces</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div style={{
        padding: '16px 24px',
        borderTop: '1px solid var(--border-subtle)',
        background: 'rgba(10, 13, 20, 0.8)',
        backdropFilter: 'blur(12px)',
      }}>
        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything about your data (e.g. 'Which region generated the highest revenue?')"
            disabled={isLoading}
            style={{
              flex: 1,
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '12px 16px',
              color: 'var(--text-main)',
              fontSize: '0.9rem',
              outline: 'none',
              fontFamily: 'var(--font-sans)',
            }}
            onFocus={(e) => (e.target.style.borderColor = 'var(--accent-primary)')}
            onBlur={(e) => (e.target.style.borderColor = 'var(--border-subtle)')}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="btn btn-primary"
            style={{ padding: '0 20px' }}
          >
            <Send size={16} />
            <span>Send</span>
          </button>
        </form>
      </div>
    </div>
  );
};
