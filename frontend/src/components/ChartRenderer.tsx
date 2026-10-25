import React from 'react';
import { BarChart3 } from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
  Legend,
} from 'recharts';

export interface ChartSpec {
  type: 'bar' | 'line' | 'pie' | 'scatter';
  title: string;
  description?: string;
  xAxisKey: string;
  yAxisKeys: string[];
  data: any[];
}

interface ChartRendererProps {
  spec: ChartSpec;
}

const COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#3b82f6'];

// Axis tick that wraps long category names onto multiple centered lines
const WrappedTick: React.FC<any> = ({ x, y, payload }) => {
  const value = String(payload?.value ?? '');
  const maxLen = 14;
  const lines: string[] = [];
  let rest = value;
  while (rest.length > maxLen) {
    let cut = rest.lastIndexOf(' ', maxLen);
    if (cut <= 0) cut = maxLen;
    lines.push(rest.slice(0, cut).trim());
    rest = rest.slice(cut).trim();
  }
  if (rest) lines.push(rest);
  return (
    <text x={x} y={y} textAnchor="middle" fill="#64748b" fontSize={11}>
      {lines.slice(0, 3).map((ln, i) => (
        <tspan key={i} x={x} dy={i === 0 ? 10 : 12}>
          {ln}
        </tspan>
      ))}
    </text>
  );
};

export const ChartRenderer: React.FC<ChartRendererProps> = ({ spec }) => {
  if (!spec || !spec.data || spec.data.length === 0) {
    return null;
  }

  const { type, title, description, xAxisKey, yAxisKeys, data } = spec;

  // Defensive: only keep rows where at least one Y axis has a plottable number.
  // Numeric-looking strings ("12,345.60") are coerced; anything else is dropped.
  const toNum = (v: any): number | null => {
    if (typeof v === 'number') return Number.isFinite(v) ? v : null;
    if (typeof v === 'boolean') return null;
    if (typeof v === 'string') {
      const n = parseFloat(v.replace(/[,\s$]/g, ''));
      return Number.isFinite(n) ? n : null;
    }
    return null;
  };
  const plotData = data
    .map((row: any) => {
      if (!row || typeof row !== 'object') return null;
      const coerced: any = { ...row };
      let anyNumeric = false;
      for (const k of yAxisKeys) {
        const n = toNum(row[k]);
        if (n === null) { coerced[k] = null; } else { coerced[k] = n; anyNumeric = true; }
      }
      return anyNumeric ? coerced : null;
    })
    .filter(Boolean) as any[];

  if (plotData.length === 0) {
    return (
      <div
        className="chart-enter glass-panel"
        style={{
          padding: '24px 20px',
          marginTop: '14px',
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          color: 'var(--text-muted)',
          fontSize: '0.8rem',
        }}
      >
        <BarChart3 size={18} color="#64748b" />
        <span>
          No plottable numeric data returned for this query — try asking for an
          aggregation (e.g. "revenue by region").
        </span>
      </div>
    );
  }

  // Format tooltip
  const customTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: 'rgba(15, 23, 42, 0.95)',
          border: '1px solid var(--border-accent)',
          borderRadius: '8px',
          padding: '8px 12px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
          fontSize: '0.8rem',
        }}>
          <p style={{ color: '#94a3b8', margin: '0 0 4px 0', fontWeight: 600 }}>{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={`item-${index}`} style={{ color: entry.color || '#38bdf8', margin: 0, fontWeight: 500 }}>
              {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // Wrap axis labels when categories are long or numerous; never skip ticks
  const needsWrap = plotData.length > 6 || plotData.some((d: any) => String(d[xAxisKey] ?? '').length > 14);
  const xAxisProps = {
    dataKey: xAxisKey,
    interval: 0 as const,
    height: needsWrap ? 60 : 30,
    tick: <WrappedTick />,
    tickLine: false,
  };

  return (
    <div className="chart-enter glass-panel" style={{ padding: '16px 20px', marginTop: '14px', width: '100%' }}>
      <div style={{ marginBottom: '14px' }}>
        <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f3f4f6', margin: 0 }}>{title}</h4>
        {description && (
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '2px 0 0 0' }}>{description}</p>
        )}
      </div>

      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          {type === 'line' ? (
            <LineChart data={plotData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" />
              <XAxis stroke="#64748b" {...xAxisProps} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={(v) => (v >= 1000 ? `${(v/1000).toFixed(0)}k` : v)} />
              <Tooltip content={customTooltip} />
              {yAxisKeys.map((key, i) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={COLORS[i % COLORS.length]}
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: COLORS[i % COLORS.length] }}
                  activeDot={{ r: 6 }}
                />
              ))}
            </LineChart>
          ) : type === 'pie' ? (
            <PieChart>
              <Pie
                data={plotData}
                dataKey={yAxisKeys[0]}
                nameKey={xAxisKey}
                cx="50%"
                cy="50%"
                outerRadius={85}
                innerRadius={45}
                paddingAngle={4}
              >
                {plotData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={customTooltip} />
              <Legend wrapperStyle={{ fontSize: '0.75rem', color: '#94a3b8' }} />
            </PieChart>
          ) : type === 'scatter' ? (
            <ScatterChart margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" />
              <XAxis dataKey={xAxisKey} stroke="#64748b" fontSize={11} name={xAxisKey} />
              <YAxis dataKey={yAxisKeys[0]} stroke="#64748b" fontSize={11} name={yAxisKeys[0]} />
              <Tooltip content={customTooltip} />
              <Scatter name="Data Points" data={plotData} fill="#6366f1" />
            </ScatterChart>
          ) : (
            <BarChart data={plotData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" />
              <XAxis stroke="#64748b" {...xAxisProps} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={(v) => (v >= 1000 ? `${(v/1000).toFixed(0)}k` : v)} />
              <Tooltip content={customTooltip} />
              {yAxisKeys.map((key, i) => (
                <Bar key={key} dataKey={key} fill={COLORS[i % COLORS.length]} radius={[4, 4, 0, 0]} />
              ))}
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
};
