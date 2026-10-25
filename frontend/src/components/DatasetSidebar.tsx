import React from 'react';
import { Link2, Sparkles, FileSpreadsheet, Download } from 'lucide-react';

export interface TableMeta {
  name: string;
  row_count: number;
  column_count: number;
  health_score: number;
  warnings: string[];
}

export interface Relationship {
  source_table: string;
  source_column: string;
  target_table: string;
  target_column: string;
  description: string;
}

interface DatasetSidebarProps {
  tables: TableMeta[];
  relationships: Relationship[];
  onSelectPrompt: (prompt: string) => void;
  selectedTable: string | null;
  onSelectTable: (tableName: string) => void;
}

const EXAMPLE_PROMPTS = [
  "Which region generated the highest revenue?",
  "Show monthly sales trends.",
  "Which products are underperforming?",
  "What are the top five customers?",
  "Generate SQL for this analysis.",
  "Detect anomalies in the dataset.",
];

export const DatasetSidebar: React.FC<DatasetSidebarProps> = ({
  tables,
  relationships,
  onSelectPrompt,
  selectedTable,
  onSelectTable,
}) => {
  return (
    <aside style={{
      width: '320px',
      minWidth: '320px',
      height: '100%',
      overflowY: 'auto',
      borderRight: '1px solid var(--border-subtle)',
      background: 'rgba(12, 17, 28, 0.7)',
      padding: '20px 16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '24px',
    }}>
      {/* Tables Section */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileSpreadsheet size={16} color="#818cf8" />
            <h2 style={{ fontSize: '0.85rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
              Active Datasets ({tables.length})
            </h2>
          </div>
        </div>

        {tables.length === 0 ? (
          <div style={{
            padding: '20px 14px',
            textAlign: 'center',
            background: 'rgba(255, 255, 255, 0.02)',
            borderRadius: '8px',
            border: '1px dashed var(--border-subtle)',
            color: 'var(--text-dim)',
            fontSize: '0.82rem',
          }}>
            No CSV datasets loaded yet.<br />Click <strong>Upload CSV</strong> or <strong>Load Samples</strong> above to begin.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {tables.map((tbl) => {
              const isSelected = selectedTable === tbl.name;
              return (
                <div
                  key={tbl.name}
                  onClick={() => onSelectTable(tbl.name)}
                  style={{
                    padding: '10px 12px',
                    borderRadius: '8px',
                    background: isSelected ? 'rgba(99, 102, 241, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                    border: `1px solid ${isSelected ? 'rgba(99, 102, 241, 0.4)' : 'var(--border-subtle)'}`,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.875rem', color: isSelected ? '#a5b4fc' : 'var(--text-main)' }}>
                      {tbl.name}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          window.open(`/api/tables/${tbl.name}/export-csv`, '_blank');
                        }}
                        title="Download cleaned CSV"
                        style={{
                          background: 'transparent',
                          border: 'none',
                          cursor: 'pointer',
                          color: '#38bdf8',
                          padding: '2px',
                          display: 'flex',
                          alignItems: 'center',
                        }}
                      >
                        <Download size={14} />
                      </button>
                      <span style={{
                        fontSize: '0.7rem',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: tbl.health_score >= 80 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                        color: tbl.health_score >= 80 ? '#34d399' : '#fbbf24',
                      }}>
                        Score: {tbl.health_score}%
                      </span>
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    <span>{tbl.row_count.toLocaleString()} rows</span>
                    <span>•</span>
                    <span>{tbl.column_count} cols</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Relational Foreign Keys */}
      {relationships.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <Link2 size={16} color="#06b6d4" />
            <h2 style={{ fontSize: '0.85rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
              Multi-File Joins ({relationships.length})
            </h2>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {relationships.map((rel, i) => (
              <div
                key={i}
                style={{
                  padding: '8px 10px',
                  borderRadius: '6px',
                  background: 'rgba(6, 182, 212, 0.06)',
                  border: '1px solid rgba(6, 182, 212, 0.2)',
                  fontSize: '0.75rem',
                }}
              >
                <div style={{ fontWeight: 600, color: '#67e8f9' }}>
                  {rel.source_table}.{rel.source_column} ➔ {rel.target_table}.{rel.target_column}
                </div>
                <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem', marginTop: '2px' }}>
                  Multi-table JOIN enabled
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Example Assignment Questions */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <Sparkles size={16} color="#f59e0b" />
          <h2 style={{ fontSize: '0.85rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
            Assignment Questions
          </h2>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {EXAMPLE_PROMPTS.map((prompt, i) => (
            <button
              key={i}
              onClick={() => onSelectPrompt(prompt)}
              style={{
                textAlign: 'left',
                padding: '8px 10px',
                borderRadius: '6px',
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-main)',
                fontSize: '0.8rem',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)')}
            >
              "{prompt}"
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
};
