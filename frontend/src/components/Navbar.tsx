import React from 'react';
import { Database, Terminal, UploadCloud, PlayCircle, Trash2, Cpu, CheckCircle2 } from 'lucide-react';

interface NavbarProps {
  tableCount: number;
  totalRows: number;
  isLogsOpen: boolean;
  onToggleLogs: () => void;
  onUploadClick: () => void;
  onLoadSamples: () => void;
  onResetDb: () => void;
  activeModel: string;
  isAgentRunning: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  tableCount,
  totalRows,
  isLogsOpen,
  onToggleLogs,
  onUploadClick,
  onLoadSamples,
  onResetDb,
  activeModel,
  isAgentRunning,
}) => {
  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '12px 24px',
      borderBottom: '1px solid var(--border-subtle)',
      background: 'rgba(10, 13, 20, 0.85)',
      backdropFilter: 'blur(16px)',
      position: 'sticky',
      top: 0,
      zIndex: 50,
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: '10px',
          background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 16px rgba(99, 102, 241, 0.4)'
        }}>
          <Database size={20} color="#ffffff" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '1.1rem', fontWeight: 700, letterSpacing: '-0.02em', margin: 0 }}>
              AI-Powered Data Analyst
            </h1>
            <span style={{
              fontSize: '0.65rem',
              fontWeight: 600,
              padding: '2px 6px',
              borderRadius: '4px',
              background: 'rgba(99, 102, 241, 0.2)',
              color: '#818cf8',
              border: '1px solid rgba(99, 102, 241, 0.3)',
              textTransform: 'uppercase'
            }}>
              EDA Multi-Agent
            </span>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: 0 }}>
            LangGraph + NVIDIA Nemotron 30B (Groq Fallback) + SQLite
          </p>
        </div>
      </div>

      {/* Center Status Indicators */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* Model Badge */}
        <div className="status-pill primary" title="Primary model with automatic Groq failover">
          <Cpu size={14} className={isAgentRunning ? "pulse-indicator" : ""} />
          <span>{activeModel}</span>
        </div>

        {/* Database Status */}
        <div className="status-pill success">
          <CheckCircle2 size={14} />
          <span>{tableCount} {tableCount === 1 ? 'Table' : 'Tables'} ({totalRows.toLocaleString()} rows)</span>
        </div>
      </div>

      {/* Right Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <button
          onClick={onUploadClick}
          className="btn btn-secondary"
          title="Upload single or multiple CSV files"
        >
          <UploadCloud size={16} />
          <span>Upload CSV</span>
        </button>

        <button
          onClick={onLoadSamples}
          className="btn btn-primary"
          title="1-Click Load Customers, Products & Sales samples"
        >
          <PlayCircle size={16} />
          <span>Load Samples</span>
        </button>

        <button
          onClick={onResetDb}
          className="btn btn-danger"
          style={{ padding: '8px 10px' }}
          title="Clear SQLite database"
        >
          <Trash2 size={16} />
        </button>

        <div style={{ width: '1px', height: '24px', background: 'var(--border-subtle)', margin: '0 4px' }} />

        {/* Logs Drawer Toggle */}
        <button
          onClick={onToggleLogs}
          className={`btn ${isLogsOpen ? 'btn-primary' : 'btn-secondary'}`}
          style={{ position: 'relative' }}
          title="Toggle live active backend agent logs"
        >
          <Terminal size={16} />
          <span>Active Logs</span>
          {isAgentRunning && (
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: '#10b981',
              boxShadow: '0 0 8px #10b981',
              position: 'absolute',
              top: '6px',
              right: '6px',
            }} />
          )}
        </button>
      </div>
    </header>
  );
};
