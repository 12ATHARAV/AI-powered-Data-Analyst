import React, { useState, useEffect, useRef } from 'react';
import { Terminal, X, Trash2, ArrowDownCircle, Maximize2, Minimize2, GripHorizontal } from 'lucide-react';

export interface LogItem {
  timestamp: string;
  agent: string;
  action: string;
  level: 'info' | 'warn' | 'error' | 'success';
  details?: any;
}

interface LiveLogsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  logs: LogItem[];
  onClearLogs: () => void;
}

export const LiveLogsDrawer: React.FC<LiveLogsDrawerProps> = ({
  isOpen,
  onClose,
  logs,
  onClearLogs,
}) => {
  const [filter, setFilter] = useState<'all' | 'clean' | 'sql' | 'anomaly' | 'failover'>('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const [height, setHeight] = useState<number>(340);
  const [isDragging, setIsDragging] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logic
  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  // Drag-to-resize handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const newHeight = window.innerHeight - moveEvent.clientY;
      const clampedHeight = Math.max(140, Math.min(window.innerHeight * 0.85, newHeight));
      setHeight(clampedHeight);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  if (!isOpen) return null;

  const filteredLogs = logs.filter((log) => {
    const a = log.agent.toLowerCase();
    const act = log.action.toLowerCase();
    if (filter === 'clean') return a.includes('clean') || act.includes('clean') || act.includes('remediat') || act.includes('casing') || act.includes('dedup');
    if (filter === 'sql') return a.includes('sql') || act.includes('sql') || a.includes('coder');
    if (filter === 'anomaly') return a.includes('anomaly') || act.includes('anomaly') || act.includes('outlier');
    if (filter === 'failover') return a.includes('failover') || log.level === 'warn';
    return true;
  });

  const getAgentBadgeColor = (agent: string) => {
    const a = agent.toLowerCase();
    if (a.includes('clean') || a.includes('ingest')) return { bg: 'rgba(16, 185, 129, 0.2)', text: '#34d399', border: 'rgba(16, 185, 129, 0.4)' };
    if (a.includes('supervisor')) return { bg: 'rgba(99, 102, 241, 0.2)', text: '#818cf8', border: 'rgba(99, 102, 241, 0.3)' };
    if (a.includes('sql') || a.includes('coder')) return { bg: 'rgba(6, 182, 212, 0.2)', text: '#38bdf8', border: 'rgba(6, 182, 212, 0.3)' };
    if (a.includes('anomaly')) return { bg: 'rgba(245, 158, 11, 0.2)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)' };
    if (a.includes('viz') || a.includes('visual')) return { bg: 'rgba(52, 211, 153, 0.2)', text: '#34d399', border: 'rgba(52, 211, 153, 0.3)' };
    if (a.includes('failover')) return { bg: 'rgba(239, 68, 68, 0.2)', text: '#f87171', border: 'rgba(239, 68, 68, 0.4)' };
    return { bg: 'rgba(168, 85, 247, 0.2)', text: '#c084fc', border: 'rgba(168, 85, 247, 0.3)' };
  };

  return (
    <div style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      height: `${height}px`,
      background: '#07090e',
      borderTop: '1px solid var(--border-accent)',
      zIndex: 100,
      boxShadow: '0 -8px 30px rgba(0, 0, 0, 0.75)',
      display: 'flex',
      flexDirection: 'column',
      userSelect: isDragging ? 'none' : 'auto',
    }}>
      {/* Draggable Resizer Bar */}
      <div
        onMouseDown={handleMouseDown}
        style={{
          height: '10px',
          background: isDragging ? 'rgba(99, 102, 241, 0.4)' : 'rgba(255, 255, 255, 0.04)',
          cursor: 'row-resize',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          transition: 'background 0.15s ease',
        }}
        title="Drag up or down to resize logs panel"
      >
        <GripHorizontal size={14} color={isDragging ? '#818cf8' : 'rgba(255, 255, 255, 0.3)'} />
      </div>

      {/* Header Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '6px 16px',
        borderBottom: '1px solid var(--border-subtle)',
        background: 'rgba(18, 24, 38, 0.95)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Terminal size={16} color="#6366f1" />
          <span style={{ fontSize: '0.85rem', fontWeight: 600, letterSpacing: '0.03em', fontFamily: 'var(--font-mono)' }}>
            ACTIVE BACKEND AGENT LOGS & PROCESS TRACE
          </span>
          <span style={{
            fontSize: '0.7rem',
            padding: '1px 6px',
            borderRadius: '4px',
            background: 'rgba(255, 255, 255, 0.08)',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
          }}>
            {filteredLogs.length} events
          </span>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>
            (drag top border to resize)
          </span>
        </div>

        {/* Filter Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {(['all', 'clean', 'sql', 'anomaly', 'failover'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setFilter(mode)}
              style={{
                background: filter === mode ? 'rgba(99, 102, 241, 0.3)' : 'transparent',
                color: filter === mode ? '#ffffff' : 'var(--text-dim)',
                border: `1px solid ${filter === mode ? '#6366f1' : 'transparent'}`,
                borderRadius: '4px',
                padding: '2px 8px',
                fontSize: '0.72rem',
                cursor: 'pointer',
                textTransform: 'uppercase',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {mode}
            </button>
          ))}
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className="btn btn-secondary"
            style={{ padding: '4px 8px', fontSize: '0.72rem' }}
            title="Auto-scroll to bottom"
          >
            <ArrowDownCircle size={14} color={autoScroll ? '#10b981' : 'var(--text-dim)'} />
            <span>Scroll</span>
          </button>

          <button
            onClick={() => setHeight(height > 450 ? 240 : 550)}
            className="btn btn-secondary"
            style={{ padding: '4px 8px', fontSize: '0.72rem' }}
            title={height > 450 ? 'Minimize height' : 'Expand height'}
          >
            {height > 450 ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>

          <button
            onClick={onClearLogs}
            className="btn btn-secondary"
            style={{ padding: '4px 8px', fontSize: '0.72rem' }}
            title="Clear logs"
          >
            <Trash2 size={13} />
          </button>

          <button
            onClick={onClose}
            className="btn btn-secondary"
            style={{ padding: '4px 8px' }}
            title="Close drawer"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Log Feed */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '12px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        background: '#07090e',
      }}>
        {filteredLogs.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', fontSize: '0.8rem', fontFamily: 'var(--font-mono)', padding: '24px 0', textAlign: 'center' }}>
            No agent events recorded yet in this category. Perform data actions or ask questions to inspect live logs.
          </div>
        ) : (
          filteredLogs.map((log, idx) => {
            const badge = getAgentBadgeColor(log.agent);
            return (
              <div key={idx} className="terminal-line" style={{ display: 'flex', flexWrap: 'wrap' }}>
                <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem', minWidth: '65px' }}>
                  {log.timestamp}
                </span>

                <span style={{
                  padding: '1px 6px',
                  borderRadius: '4px',
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  background: badge.bg,
                  color: badge.text,
                  border: `1px solid ${badge.border}`,
                  whiteSpace: 'nowrap',
                }}>
                  {log.agent}
                </span>

                <span style={{
                  color: log.level === 'warn' ? '#fbbf24' : log.level === 'success' ? '#34d399' : '#e5e7eb',
                  flex: 1,
                  wordBreak: 'break-word',
                }}>
                  {log.action}
                </span>

                {log.details && log.details.sql && (
                  <div style={{
                    display: 'block',
                    width: '100%',
                    marginLeft: '75px',
                    padding: '6px 10px',
                    background: 'rgba(255, 255, 255, 0.03)',
                    borderRadius: '4px',
                    color: '#67e8f9',
                    fontSize: '0.75rem',
                    marginTop: '2px',
                  }}>
                    <code>{log.details.sql}</code>
                  </div>
                )}
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};
