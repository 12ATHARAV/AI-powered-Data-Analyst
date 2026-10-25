import React, { useEffect, useState } from 'react';
import { ShieldCheck, CheckCircle2, AlertTriangle, ArrowRight, RefreshCw, Sparkles, Database, Wrench, FileWarning } from 'lucide-react';

interface CasingFix {
  column: string;
  original: string;
  remediated: string;
  count: number;
  reason: string;
}

interface DomainFix {
  row_identifier: string;
  column: string;
  original_value: any;
  remediated_value: any;
  action: string;
  reason: string;
}

interface ImputationFix {
  column: string;
  missing_count: number;
  imputed_value: string;
  action: string;
  reason: string;
}

interface CleaningAudit {
  table_name: string;
  initial_rows: number;
  final_rows: number;
  duplicates_removed: number;
  health_score_before: number;
  health_score_after: number;
  total_fixes_applied: number;
  casing_fixes: CasingFix[];
  domain_fixes: DomainFix[];
  imputation_fixes?: ImputationFix[];
  outlier_fixes: any[];
  structural_fixes?: any[];
}

export const CleaningAuditView: React.FC = () => {
  const [audits, setAudits] = useState<CleaningAudit[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTable, setSelectedTable] = useState<string>('all');

  const fetchAudits = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/cleaning/audit');
      const data = await res.json();
      setAudits(data);
    } catch (e) {
      console.error('Failed to load cleaning audits:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAudits();
  }, []);

  const totalDuplicates = audits.reduce((acc, a) => acc + (a.duplicates_removed || 0), 0);
  const totalCasingFixes = audits.reduce((acc, a) => acc + (a.casing_fixes?.reduce((sum, f) => sum + f.count, 0) || 0), 0);
  const totalDomainFixes = audits.reduce((acc, a) => acc + (a.domain_fixes?.length || 0), 0);
  const totalImputations = audits.reduce((acc, a) => acc + (a.imputation_fixes?.reduce((sum, f) => sum + f.missing_count, 0) || 0), 0);

  const filteredAudits = selectedTable === 'all' 
    ? audits 
    : audits.filter((a) => a.table_name === selectedTable);

  if (loading) {
    return (
      <div style={{ padding: '60px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
        <RefreshCw size={28} className="pulse-indicator" style={{ margin: '0 auto 12px auto' }} />
        <p>Loading dataset cleaning audit reports and remediation logs...</p>
      </div>
    );
  }

  if (audits.length === 0) {
    return (
      <div style={{ padding: '60px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
        <ShieldCheck size={36} color="#64748b" style={{ margin: '0 auto 12px auto' }} />
        <h3 style={{ fontSize: '1.1rem', color: '#f3f4f6', marginBottom: '8px' }}>No Cleaning Audits Yet</h3>
        <p style={{ fontSize: '0.85rem' }}>Upload CSV files or click <strong>Load Samples</strong> in the top bar to inspect automatic data cleaning & remediation.</p>
      </div>
    );
  }

  return (
    <div style={{
      padding: '24px 32px',
      overflowY: 'auto',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      gap: '24px',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 700, margin: 0 }}>
              Data Quality Audit & Remediation Log
            </h2>
            <span style={{
              fontSize: '0.75rem',
              padding: '2px 8px',
              borderRadius: '4px',
              background: 'rgba(16, 185, 129, 0.2)',
              color: '#34d399',
              fontWeight: 600,
            }}>
              Automated Cleaning Active
            </span>
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
            Complete audit trail detailing what was corrupted in the raw CSVs and the exact data engineering actions taken to remediate them.
          </p>
        </div>

        <button onClick={fetchAudits} className="btn btn-secondary">
          <RefreshCw size={14} />
          <span>Refresh Audit</span>
        </button>
      </div>

      {/* KPI Cards: What Was Wrong & What Was Fixed */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '16px',
      }}>
        {/* Duplicates */}
        <div className="glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Duplicates Dropped
            </span>
            <CheckCircle2 size={18} color="#10b981" />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#f3f4f6' }}>
            {totalDuplicates} Rows
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', margin: '6px 0 0 0' }}>
            Purged redundant exact copies to prevent revenue double-counting.
          </p>
        </div>

        {/* Casing Inconsistencies */}
        <div className="glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Casing Inconsistencies
            </span>
            <Wrench size={18} color="#38bdf8" />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#38bdf8' }}>
            {totalCasingFixes} Values
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', margin: '6px 0 0 0' }}>
            Standardized dirty variants (e.g. ' east', 'EAST' ➔ 'East').
          </p>
        </div>

        {/* Imputed Values */}
        <div className="glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Missing Data Imputed
            </span>
            <Sparkles size={18} color="#c084fc" />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#c084fc' }}>
            {totalImputations} Imputations
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', margin: '6px 0 0 0' }}>
            Contextually imputed missing values via customer history & modal fallback.
          </p>
        </div>

        {/* Domain Corrections */}
        <div className="glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Domain Violations Fixed
            </span>
            <ShieldCheck size={18} color="#fbbf24" />
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#fbbf24' }}>
            {totalDomainFixes} Records
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', margin: '6px 0 0 0' }}>
            Rectified sign-inversion errors in revenue & quantity measures.
          </p>
        </div>
      </div>

      {/* Table Filter Tabs */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <button
          onClick={() => setSelectedTable('all')}
          className={`btn ${selectedTable === 'all' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ fontSize: '0.8rem', padding: '6px 12px' }}
        >
          All Datasets ({audits.length})
        </button>
        {audits.map((a) => (
          <button
            key={a.table_name}
            onClick={() => setSelectedTable(a.table_name)}
            className={`btn ${selectedTable === a.table_name ? 'btn-primary' : 'btn-secondary'}`}
            style={{ fontSize: '0.8rem', padding: '6px 12px' }}
          >
            {a.table_name}
          </button>
        ))}
      </div>

      {/* Detailed Audit Cards per Table */}
      {filteredAudits.map((audit) => (
        <div key={audit.table_name} className="glass-panel" style={{ padding: '24px' }}>
          {/* Table Header & Before/After Score */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Database size={20} color="#818cf8" />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>
                Table: {audit.table_name}
              </h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {audit.initial_rows.toLocaleString()} Initial Rows ➔ {audit.final_rows.toLocaleString()} Clean Rows
              </span>
            </div>

            {/* Health Score Uplift Badge */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Health Score:</span>
              <span style={{
                fontSize: '0.85rem',
                fontWeight: 700,
                color: '#f87171',
                background: 'rgba(239, 68, 68, 0.15)',
                padding: '2px 8px',
                borderRadius: '4px',
              }}>
                Before: {audit.health_score_before}%
              </span>
              <ArrowRight size={14} color="#94a3b8" />
              <span style={{
                fontSize: '0.85rem',
                fontWeight: 700,
                color: '#34d399',
                background: 'rgba(16, 185, 129, 0.2)',
                padding: '2px 8px',
                borderRadius: '4px',
              }}>
                After: {audit.health_score_after}%
              </span>
            </div>
          </div>

          {/* Section 0: Structural (Header/Encoding) Fixes */}
          {audit.structural_fixes && audit.structural_fixes.length > 0 && (
            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ fontSize: '0.88rem', fontWeight: 600, color: '#a5b4fc', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <FileWarning size={15} />
                <span>Structural Header & Encoding Fixes</span>
              </h4>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-dim)' }}>
                      <th style={{ padding: '8px 12px' }}>Column</th>
                      <th style={{ padding: '8px 12px' }}>Original</th>
                      <th style={{ padding: '8px 12px' }}>Fixed</th>
                      <th style={{ padding: '8px 12px' }}>Action</th>
                      <th style={{ padding: '8px 12px' }}>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {audit.structural_fixes.map((f: any, i: number) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 600, color: '#f3f4f6' }}>{f.column}</td>
                        <td style={{ padding: '10px 12px', color: '#f87171', fontFamily: 'var(--font-mono)' }}>
                          {String(f.original)}
                        </td>
                        <td style={{ padding: '10px 12px', color: '#34d399', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                          {String(f.new)}
                        </td>
                        <td style={{ padding: '10px 12px', color: '#a5b4fc' }}>{f.action}</td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{f.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Section 1: Inconsistent Casing & Whitespace Remediation */}
          {audit.casing_fixes && audit.casing_fixes.length > 0 && (
            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ fontSize: '0.88rem', fontWeight: 600, color: '#38bdf8', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Wrench size={15} />
                <span>Categorical Casing & Whitespace Normalization</span>
              </h4>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-dim)' }}>
                      <th style={{ padding: '8px 12px' }}>Column</th>
                      <th style={{ padding: '8px 12px' }}>Raw Dirty Value</th>
                      <th style={{ padding: '8px 12px' }}>Remediated Canonical Value</th>
                      <th style={{ padding: '8px 12px' }}>Rows Affected</th>
                      <th style={{ padding: '8px 12px' }}>Reason & Principle</th>
                    </tr>
                  </thead>
                  <tbody>
                    {audit.casing_fixes.map((f, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 600, color: '#f3f4f6' }}>{f.column}</td>
                        <td style={{ padding: '10px 12px', color: '#f87171', fontFamily: 'var(--font-mono)' }}>
                          "{f.original}"
                        </td>
                        <td style={{ padding: '10px 12px', color: '#34d399', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                          "{f.remediated}"
                        </td>
                        <td style={{ padding: '10px 12px', fontWeight: 600 }}>{f.count}</td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{f.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Section 2: Deduplication Report */}
          {audit.duplicates_removed > 0 && (
            <div style={{
              marginBottom: '20px',
              padding: '12px 16px',
              borderRadius: '8px',
              background: 'rgba(16, 185, 129, 0.06)',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              fontSize: '0.82rem',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <CheckCircle2 size={16} color="#10b981" />
                <strong style={{ color: '#34d399' }}>
                  Deduplication Principle: Exact Row Match Removal
                </strong>
              </div>
              <p style={{ color: 'var(--text-muted)', margin: 0 }}>
                Identified <strong>{audit.duplicates_removed} duplicate rows</strong> in {audit.table_name}. 
                Applied standard policy: preserved first chronological transaction record and removed redundant copies to ensure metric accuracy.
              </p>
            </div>
          )}

          {/* Section 3: Categorical Imputation */}
          {audit.imputation_fixes && audit.imputation_fixes.length > 0 && (
            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ fontSize: '0.88rem', fontWeight: 600, color: '#c084fc', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Sparkles size={15} />
                <span>Missing Categorical Imputations</span>
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {audit.imputation_fixes.map((imp, idx) => (
                  <div key={idx} style={{
                    padding: '10px 14px',
                    borderRadius: '6px',
                    background: 'rgba(192, 132, 252, 0.06)',
                    border: '1px solid rgba(192, 132, 252, 0.2)',
                    fontSize: '0.8rem',
                  }}>
                    <strong style={{ color: '#c084fc' }}>{imp.column}: </strong>
                    <span style={{ color: 'var(--text-main)' }}>{imp.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section 4: Domain & Sign Inversion Fixes */}
          {audit.domain_fixes && audit.domain_fixes.length > 0 && (
            <div>
              <h4 style={{ fontSize: '0.88rem', fontWeight: 600, color: '#fbbf24', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <AlertTriangle size={15} />
                <span>Business Rule & Sign Inversion Corrections</span>
              </h4>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-dim)' }}>
                      <th style={{ padding: '8px 12px' }}>Row / ID</th>
                      <th style={{ padding: '8px 12px' }}>Metric Column</th>
                      <th style={{ padding: '8px 12px' }}>Corrupted Value</th>
                      <th style={{ padding: '8px 12px' }}>Remediated Value</th>
                      <th style={{ padding: '8px 12px' }}>Action & Justification</th>
                    </tr>
                  </thead>
                  <tbody>
                    {audit.domain_fixes.map((df, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 600, color: '#f3f4f6' }}>{df.row_identifier}</td>
                        <td style={{ padding: '10px 12px', color: '#94a3b8' }}>{df.column}</td>
                        <td style={{ padding: '10px 12px', color: '#f87171', fontFamily: 'var(--font-mono)' }}>
                          {df.original_value}
                        </td>
                        <td style={{ padding: '10px 12px', color: '#34d399', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                          {df.remediated_value}
                        </td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{df.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
