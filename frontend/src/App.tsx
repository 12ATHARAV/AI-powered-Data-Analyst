import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { DatasetSidebar } from './components/DatasetSidebar';
import type { TableMeta, Relationship } from './components/DatasetSidebar';
import { ChatArea } from './components/ChatArea';
import type { ChatMessage } from './components/ChatArea';
import { DashboardView } from './components/DashboardView';
import { EDAReportView } from './components/EDAReportView';
import { CleaningAuditView } from './components/CleaningAuditView';
import { LiveLogsDrawer } from './components/LiveLogsDrawer';
import type { LogItem } from './components/LiveLogsDrawer';
import { MessageSquare, LayoutDashboard, FileText, ShieldCheck } from 'lucide-react';

export const App: React.FC = () => {
  const [tables, setTables] = useState<TableMeta[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'chat' | 'dashboard' | 'cleaning' | 'eda'>('chat');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [isLogsOpen, setIsLogsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [activeModel, setActiveModel] = useState<string>('NVIDIA Nemotron 30B');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchTables = async () => {
    try {
      const res = await fetch('/api/tables');
      const data = await res.json();
      setTables(data);
      if (data.length > 0 && !selectedTable) {
        setSelectedTable(data[0].name);
      }
    } catch (e) {
      console.error('Failed to fetch tables:', e);
    }
  };

  const fetchRelationships = async () => {
    try {
      const res = await fetch('/api/relationships');
      const data = await res.json();
      setRelationships(data);
    } catch (e) {
      console.error('Failed to fetch relationships:', e);
    }
  };

  useEffect(() => {
    fetchTables();
    fetchRelationships();
  }, []);

  const totalRows = tables.reduce((acc: number, tbl: TableMeta) => acc + tbl.row_count, 0);

  const handleUploadFiles = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const formData = new FormData();
    for (let i = 0; i < e.target.files.length; i++) {
      formData.append('files', e.target.files[i]);
    }

    try {
      setIsLoading(true);
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        await fetchTables();
        await fetchRelationships();
        setIsLogsOpen(true); // Show the real backend pipeline trace
        setLogs((prev) => [
          ...prev,
          ...buildIngestionLogs(
            (data.tables_created ?? []).map((t: any) => ({ ...t, filename: t.original_file })),
            data.relationships_detected ?? [],
            new Date().toLocaleTimeString(),
          ),
        ]);
      } else {
        alert(data.detail || 'Upload failed');
      }
    } catch (err: any) {
      alert(`Error uploading file: ${err.message}`);
    } finally {
      setIsLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Builds Active-Log entries from the REAL backend ingestion response
  // (actual row counts, cleaning audit deltas, and detected relationships)
  const buildIngestionLogs = (
    tablesData: Array<{ table_name: string; filename?: string; metadata?: any; quality?: any; cleaning_audit?: any }>,
    relationships: any[],
    now: string,
  ): LogItem[] => {
    const logs: LogItem[] = [];
    for (const t of tablesData) {
      const meta = t.metadata ?? {};
      const audit = t.cleaning_audit ?? meta.cleaning_audit ?? {};
      const cols = Array.isArray(meta.columns) ? meta.columns.length : '?';
      logs.push({
        timestamp: now,
        agent: 'Data Ingestion',
        action: `Ingested ${t.filename ?? 'CSV'} into table '${t.table_name}': ${meta.row_count ?? '?'} rows, ${cols} columns`,
        level: 'info',
      });

      const dupes = audit.duplicates_removed ?? 0;
      const casingCount = (audit.casing_fixes ?? []).reduce((s: number, f: any) => s + (f.count ?? 0), 0);
      const imputed = (audit.imputation_fixes ?? []).reduce((s: number, f: any) => s + (f.missing_count ?? 0), 0);
      const domain = (audit.domain_fixes ?? []).length;
      const outliers = (audit.outlier_fixes ?? []).length;

      if (casingCount > 0) {
        logs.push({
          timestamp: now,
          agent: 'Data Cleaning Agent',
          action: `Harmonized ${casingCount} inconsistent casing/whitespace values in '${t.table_name}' (e.g. ' east', 'EAST' -> 'East')`,
          level: 'success',
        });
      }
      if (imputed > 0) {
        logs.push({
          timestamp: now,
          agent: 'Data Cleaning Agent',
          action: `Imputed ${imputed} missing values in '${t.table_name}' using contextual profiles & modal fallback`,
          level: 'success',
        });
      }
      if (dupes > 0) {
        logs.push({
          timestamp: now,
          agent: 'Data Cleaning Agent',
          action: `Purged ${dupes} duplicate rows in '${t.table_name}' using first-occurrence policy (${audit.initial_rows} -> ${audit.final_rows} rows)`,
          level: 'success',
        });
      }
      if (domain > 0) {
        logs.push({
          timestamp: now,
          agent: 'Data Cleaning Agent',
          action: `Rectified ${domain} domain violations (negative values / out-of-range ratios) in '${t.table_name}'`,
          level: 'success',
        });
      }
      if (outliers > 0) {
        logs.push({
          timestamp: now,
          agent: 'Data Quality Audit',
          action: `Flagged ${outliers} statistically extreme value group(s) in '${t.table_name}' beyond 3x IQR (preserved with warning)`,
          level: 'warn',
        });
      }
      logs.push({
        timestamp: now,
        agent: 'Data Health Engine',
        action: `Health score for '${t.table_name}': ${audit.health_score_before ?? '?'}% -> ${audit.health_score_after ?? '?'}%`,
        level: 'success',
      });
    }

    if (relationships.length > 0) {
      logs.push({
        timestamp: now,
        agent: 'Relational Engine',
        action: `Mapped ${relationships.length} cross-table foreign key relationships: ${relationships
          .slice(0, 4)
          .map((r) => `${r.source_table}.${r.source_column} -> ${r.target_table}.${r.target_column}`)
          .join(', ')}${relationships.length > 4 ? ', ...' : ''}`,
        level: 'info',
      });
    }
    return logs;
  };

  const handleLoadSamples = async () => {
    try {
      setIsLoading(true);
      const res = await fetch('/api/samples/load', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        await fetchTables();
        await fetchRelationships();
        setIsLogsOpen(true);
        setLogs((prev) => [
          ...prev,
          ...buildIngestionLogs(data.tables ?? [], data.relationships ?? [], new Date().toLocaleTimeString()),
        ]);
      } else {
        alert(data.detail || 'Failed to load samples');
      }
    } catch (err: any) {
      alert(`Error loading samples: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetDb = async () => {
    if (!confirm('Are you sure you want to clear all loaded tables from SQLite?')) return;
    try {
      const res = await fetch('/api/reset', { method: 'DELETE' });
      if (res.ok) {
        setTables([]);
        setRelationships([]);
        setSelectedTable(null);
        setMessages([]);
        setLogs((prev) => [
          ...prev,
          {
            timestamp: new Date().toLocaleTimeString(),
            agent: 'System',
            action: 'Cleared all tables from SQLite database.',
            level: 'warn',
          },
        ]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendMessage = async (query: string) => {
    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `asst-${Date.now()}`;

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, sender: 'user', content: query },
      { id: assistantMsgId, sender: 'assistant', content: 'Analyzing multi-agent workflow...', modelUsed: activeModel },
    ]);

    setIsLoading(true);
    setIsLogsOpen(true); // Automatically open active logs drawer so user sees backend action!

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, session_id: 'default' }),
      });

      if (!response.body) return;

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const jsonStr = line.replace('data: ', '').trim();
          if (!jsonStr) continue;

          try {
            const event = JSON.parse(jsonStr);

            if (event.type === 'log') {
              setLogs((prev) => [...prev, event.data]);
            } else if (event.type === 'sql') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? { ...m, sql: event.data.query, pandas: event.data.pandas }
                    : m
                )
              );
            } else if (event.type === 'chart') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId ? { ...m, chartSpec: event.data } : m
                )
              );
            } else if (event.type === 'anomalies') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId ? { ...m, anomalies: event.data } : m
                )
              );
            } else if (event.type === 'complete') {
              setActiveModel(event.data.model_used || 'NVIDIA Nemotron 30B');
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? {
                        ...m,
                        content: event.data.answer,
                        reasoning: event.data.reasoning,
                        modelUsed: event.data.model_used,
                        provider: event.data.provider,
                      }
                    : m
                )
              );
            }
          } catch (e) {
            console.error('Error parsing SSE event:', e);
          }
        }
      }
    } catch (err: any) {
      console.error(err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsgId
            ? { ...m, content: `Error executing query: ${err.message}` }
            : m
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleUploadFiles}
        multiple
        accept=".csv"
        style={{ display: 'none' }}
      />

      {/* Top Navbar */}
      <Navbar
        tableCount={tables.length}
        totalRows={totalRows}
        isLogsOpen={isLogsOpen}
        onToggleLogs={() => setIsLogsOpen(!isLogsOpen)}
        onUploadClick={() => fileInputRef.current?.click()}
        onLoadSamples={handleLoadSamples}
        onResetDb={handleResetDb}
        activeModel={activeModel}
        isAgentRunning={isLoading}
      />

      {/* Main Workspace */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left Sidebar */}
        <DatasetSidebar
          tables={tables}
          relationships={relationships}
          onSelectPrompt={(p) => {
            setActiveTab('chat');
            handleSendMessage(p);
          }}
          selectedTable={selectedTable}
          onSelectTable={(t) => {
            setSelectedTable(t);
            setActiveTab('eda');
          }}
        />

        {/* Center Panel */}
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Tab Navigation */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 24px',
            borderBottom: '1px solid var(--border-subtle)',
            background: 'rgba(10, 13, 20, 0.4)',
          }}>
            <button
              onClick={() => setActiveTab('chat')}
              className={`btn ${activeTab === 'chat' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.8rem', padding: '6px 12px' }}
            >
              <MessageSquare size={14} />
              <span>Analyst Chat</span>
            </button>

            <button
              onClick={() => setActiveTab('dashboard')}
              className={`btn ${activeTab === 'dashboard' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.8rem', padding: '6px 12px' }}
            >
              <LayoutDashboard size={14} />
              <span>Executive Dashboard</span>
            </button>

            <button
              onClick={() => setActiveTab('cleaning')}
              className={`btn ${activeTab === 'cleaning' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.8rem', padding: '6px 12px' }}
            >
              <ShieldCheck size={14} />
              <span>Data Cleaning & Fixes</span>
            </button>

            <button
              onClick={() => setActiveTab('eda')}
              className={`btn ${activeTab === 'eda' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '0.8rem', padding: '6px 12px' }}
            >
              <FileText size={14} />
              <span>Full EDA Profiler</span>
            </button>
          </div>

          {/* Tab Contents */}
          <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
            {activeTab === 'chat' && (
              <ChatArea
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
                onSelectPrompt={(p) => handleSendMessage(p)}
              />
            )}

            {activeTab === 'dashboard' && <DashboardView />}

            {activeTab === 'cleaning' && <CleaningAuditView />}

            {activeTab === 'eda' && <EDAReportView tableName={selectedTable} />}
          </div>
        </main>
      </div>

      {/* Real-time Backend Logs Drawer */}
      <LiveLogsDrawer
        isOpen={isLogsOpen}
        onClose={() => setIsLogsOpen(false)}
        logs={logs}
        onClearLogs={() => setLogs([])}
      />
    </div>
  );
};
export default App;
