import React, { useEffect, useState } from 'react';
import { DollarSign, ShoppingBag, Users, AlertTriangle, RefreshCw, BarChart3, ChevronDown, ChevronUp } from 'lucide-react';
import { ChartRenderer } from './ChartRenderer';
import type { ChartSpec } from './ChartRenderer';

interface KpiItem {
  id: string;
  title: string;
  value: string;
  subtitle: string;
  trend: string;
}

export const DashboardView: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [isAnomaliesOpen, setIsAnomaliesOpen] = useState(false);
  const [data, setData] = useState<{
    has_data: boolean;
    kpis: KpiItem[];
    charts: ChartSpec[];
    anomalies: any[];
  } | null>(null);

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/dashboard/generate');
      const json = await res.json();
      setData(json);
    } catch (e) {
      console.error('Failed to load dashboard:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const getKpiIcon = (id: string) => {
    const lower = id.toLowerCase();
    if (lower.includes('revenue') || lower.includes('profit') || lower.includes('price') || lower.includes('cost')) {
      return <DollarSign size={20} color="#10b981" />;
    }
    if (lower.includes('order') || lower.includes('sold') || lower.includes('sales')) {
      return <ShoppingBag size={20} color="#6366f1" />;
    }
    if (lower.includes('cust') || lower.includes('user') || lower.includes('client')) {
      return <Users size={20} color="#06b6d4" />;
    }
    if (lower.includes('anom')) {
      return <AlertTriangle size={20} color="#f59e0b" />;
    }
    return <BarChart3 size={20} color="#8b5cf6" />;
  };

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
        <RefreshCw size={24} className="pulse-indicator" style={{ margin: '0 auto 12px auto' }} />
        <p>Generating executive dashboard across active datasets...</p>
      </div>
    );
  }

  if (!data || !data.has_data) {
    return (
      <div style={{ padding: '60px 24px', textAlign: 'center', color: 'var(--text-muted)' }}>
        <BarChart3 size={36} color="#64748b" style={{ margin: '0 auto 12px auto' }} />
        <h3 style={{ fontSize: '1.1rem', color: '#f3f4f6', marginBottom: '8px' }}>No Data Loaded for Dashboard</h3>
        <p style={{ fontSize: '0.85rem' }}>Upload your CSV files or click <strong>Load Samples</strong> in the top bar to generate the dashboard.</p>
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
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>Executive Business Dashboard</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
            Multi-file cross-sectional metrics and visualizations
          </p>
        </div>
        <button onClick={fetchDashboard} className="btn btn-secondary">
          <RefreshCw size={14} />
          <span>Refresh</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px',
      }}>
        {data.kpis.map((kpi) => (
          <div key={kpi.id} className="glass-panel" style={{ padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                {kpi.title}
              </span>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'rgba(255, 255, 255, 0.05)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                {getKpiIcon(kpi.id)}
              </div>
            </div>

            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f3f4f6', letterSpacing: '-0.02em' }}>
              {kpi.value}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '8px', fontSize: '0.75rem' }}>
              <span style={{ color: 'var(--text-dim)' }}>{kpi.subtitle}</span>
              <span style={{ color: kpi.trend.includes('+') ? '#34d399' : '#fbbf24', fontWeight: 600 }}>
                {kpi.trend}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Visual Charts Grid */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0, color: '#f3f4f6' }}>
            Visual Analytics & Trends ({data.charts.length} Visualizations)
          </h3>
        </div>

        {data.charts && data.charts.length > 0 ? (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))',
            gap: '20px',
          }}>
            {data.charts.map((chart, idx) => (
              <div key={idx} style={{ width: '100%' }}>
                <ChartRenderer spec={chart} />
              </div>
            ))}
          </div>
        ) : (
          <div className="glass-panel" style={{ padding: '28px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <p style={{ margin: 0 }}>No automated charts could be generated for this dataset structure.</p>
          </div>
        )}
      </div>

      {/* Anomalies Diagnostic Section */}
      {data.anomalies && data.anomalies.length > 0 && (
        <div className="glass-panel" style={{ padding: '16px 20px' }}>
          <div
            onClick={() => setIsAnomaliesOpen(!isAnomaliesOpen)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={18} color="#f59e0b" />
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0 }}>
                Statistical Anomaly Diagnostics ({data.anomalies.length} Flagged)
              </h3>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              <span>{isAnomaliesOpen ? 'Hide Diagnostics' : 'View Diagnostics'}</span>
              {isAnomaliesOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>
          </div>

          {isAnomaliesOpen && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '14px' }}>
              {data.anomalies.map((anom, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '10px 14px',
                    borderRadius: '6px',
                    background: 'rgba(245, 158, 11, 0.06)',
                    border: '1px solid rgba(245, 158, 11, 0.2)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: '0.8rem',
                  }}
                >
                  <div>
                    <strong style={{ color: '#fbbf24' }}>{anom.table_name}.{anom.column_name}:</strong> {anom.summary}
                  </div>
                  <span style={{
                    fontSize: '0.7rem',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    background: 'rgba(245, 158, 11, 0.2)',
                    color: '#fbbf24',
                    whiteSpace: 'nowrap',
                  }}>
                    Method: {anom.method?.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
