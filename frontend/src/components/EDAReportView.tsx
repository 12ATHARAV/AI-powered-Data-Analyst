import React, { useEffect, useState } from 'react';
import { Activity, BarChart2, GitCommit } from 'lucide-react';

interface EDAReportViewProps {
  tableName: string | null;
}

export const EDAReportView: React.FC<EDAReportViewProps> = ({ tableName }) => {
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState<any>(null);

  useEffect(() => {
    if (!tableName) return;
    setLoading(true);
    fetch(`/api/eda/profile/${tableName}`)
      .then((res) => res.json())
      .then((data) => setProfile(data))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [tableName]);

  if (!tableName) {
    return (
      <div style={{ padding: '60px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
        <Activity size={36} color="#64748b" style={{ margin: '0 auto 12px auto' }} />
        <h3 style={{ fontSize: '1.1rem', color: '#f3f4f6', marginBottom: '8px' }}>Select a Table to View Full EDA</h3>
        <p style={{ fontSize: '0.85rem' }}>Select any dataset from the left sidebar to inspect univariate distributions, skewness, and correlations.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
        <p>Computing statistical distributions and correlation matrices for <strong>{tableName}</strong>...</p>
      </div>
    );
  }

  if (!profile || profile.error) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#f87171' }}>
        <p>Failed to load profile for {tableName}: {profile?.error || 'Unknown error'}</p>
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
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 700, margin: 0 }}>
            Exploratory Data Analysis: {tableName}
          </h2>
          <span style={{
            fontSize: '0.75rem',
            padding: '2px 8px',
            borderRadius: '4px',
            background: 'rgba(99, 102, 241, 0.2)',
            color: '#818cf8',
          }}>
            {profile.total_rows.toLocaleString()} rows × {profile.total_columns} columns
          </span>
        </div>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
          Full univariate summary statistics, skewness shapes, categorical modes, and Pearson correlation matrices.
        </p>
      </div>

      {/* Univariate Numeric Stats Table */}
      {profile.numeric_stats && profile.numeric_stats.length > 0 && (
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <BarChart2 size={18} color="#818cf8" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0 }}>
              Univariate Numeric Distributions
            </h3>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-dim)' }}>
                  <th style={{ padding: '8px 12px' }}>Column</th>
                  <th style={{ padding: '8px 12px' }}>Mean</th>
                  <th style={{ padding: '8px 12px' }}>Std Dev</th>
                  <th style={{ padding: '8px 12px' }}>Min</th>
                  <th style={{ padding: '8px 12px' }}>25% (Q1)</th>
                  <th style={{ padding: '8px 12px' }}>Median</th>
                  <th style={{ padding: '8px 12px' }}>75% (Q3)</th>
                  <th style={{ padding: '8px 12px' }}>Max</th>
                  <th style={{ padding: '8px 12px' }}>IQR</th>
                  <th style={{ padding: '8px 12px' }}>Skewness</th>
                  <th style={{ padding: '8px 12px' }}>Distribution</th>
                </tr>
              </thead>
              <tbody>
                {profile.numeric_stats.map((s: any, idx: number) => (
                  <tr key={idx} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                    <td style={{ padding: '10px 12px', fontWeight: 600, color: '#f3f4f6' }}>{s.column}</td>
                    <td style={{ padding: '10px 12px' }}>{s.mean.toLocaleString()}</td>
                    <td style={{ padding: '10px 12px' }}>{s.std.toLocaleString()}</td>
                    <td style={{ padding: '10px 12px' }}>{s.min.toLocaleString()}</td>
                    <td style={{ padding: '10px 12px' }}>{s.p25.toLocaleString()}</td>
                    <td style={{ padding: '10px 12px', fontWeight: 600, color: '#38bdf8' }}>{s.median.toLocaleString()}</td>
                    <td style={{ padding: '10px 12px' }}>{s.p75.toLocaleString()}</td>
                    <td style={{ padding: '10px 12px' }}>{s.max.toLocaleString()}</td>
                    <td style={{ padding: '10px 12px' }}>{s.iqr.toLocaleString()}</td>
                    <td style={{ padding: '10px 12px' }}>{s.skewness}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        fontSize: '0.7rem',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        background: s.distribution_shape === 'symmetric' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                        color: s.distribution_shape === 'symmetric' ? '#34d399' : '#fbbf24',
                      }}>
                        {s.distribution_shape}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Strong Correlations */}
      {profile.strong_correlations && profile.strong_correlations.length > 0 && (
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <GitCommit size={18} color="#06b6d4" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0 }}>
              Strong Numeric Correlations (|r| ≥ 0.5)
            </h3>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {profile.strong_correlations.map((corr: any, i: number) => (
              <div
                key={i}
                style={{
                  padding: '12px 16px',
                  borderRadius: '8px',
                  background: 'rgba(6, 182, 212, 0.06)',
                  border: '1px solid rgba(6, 182, 212, 0.2)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, color: '#f3f4f6', fontSize: '0.85rem' }}>
                    {corr.var1} ↔ {corr.var2}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                    {corr.strength.toUpperCase()} {corr.direction.toUpperCase()} RELATION
                  </div>
                </div>
                <span style={{
                  fontSize: '0.9rem',
                  fontWeight: 700,
                  color: corr.correlation > 0 ? '#34d399' : '#f87171',
                }}>
                  r = {corr.correlation}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Categorical Breakdown */}
      {profile.categorical_stats && profile.categorical_stats.length > 0 && (
        <div className="glass-panel" style={{ padding: '20px' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '14px' }}>
            Categorical Distributions & Frequency Modes
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
            {profile.categorical_stats.map((cat: any, i: number) => (
              <div key={i} style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.85rem', color: '#818cf8' }}>{cat.column}</span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>{cat.unique_count} unique</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {cat.top_values.map((val: any, j: number) => (
                    <div key={j} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem' }}>
                      <span style={{ color: 'var(--text-main)' }}>{val.value}</span>
                      <span style={{ color: 'var(--text-dim)' }}>{val.count.toLocaleString()} ({val.percentage}%)</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
