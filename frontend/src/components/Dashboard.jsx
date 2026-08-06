import React, { useState, useEffect } from 'react';
import ChartViewer from './ChartViewer';

export default function Dashboard() {
  const [pinnedCharts, setPinnedCharts] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchPinnedCharts = async () => {
    try {
      const res = await fetch('/api/pinned-charts');
      const json = await res.json();
      if (json.success) {
        setPinnedCharts(json.data || []);
      }
    } catch (err) {
      console.error('Failed to load pinned charts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPinnedCharts();
  }, []);

  const handleUnpin = async (id) => {
    try {
      const res = await fetch(`/api/pinned-charts/${id}`, { method: 'DELETE' });
      const json = await res.json();
      if (json.success) {
        setPinnedCharts((prev) => prev.filter((c) => c.id !== id));
      }
    } catch (err) {
      console.error('Failed to unpin chart:', err);
    }
  };

  if (loading) {
    return <div style={{ padding: '2rem', color: '#94a3b8' }}>Loading pinned dashboard...</div>;
  }

  return (
    <div style={{ width: '100%', height: '100%', overflowY: 'auto', padding: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '700', background: 'linear-gradient(135deg, #38bdf8, #818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Pinned Analytics Dashboard
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.25rem' }}>
            Live, re-runnable charts pinned directly from conversational chat sessions.
          </p>
        </div>
        <button onClick={fetchPinnedCharts} className="nav-tab active">
          🔄 Refresh Charts
        </button>
      </div>

      {pinnedCharts.length === 0 ? (
        <div className="glass-card" style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
          📌 No pinned charts yet. Ask the AI agent for a chart in chat and click "Pin to Dashboard"!
        </div>
      ) : (
        <div className="dashboard-grid">
          {pinnedCharts.map((chart) => (
            <div key={chart.id} className="glass-card dashboard-card">
              <div className="dashboard-card-header">
                <span className="dashboard-card-title">{chart.title}</span>
                <button className="btn-unpin" onClick={() => handleUnpin(chart.id)}>
                  Unpin ✖
                </button>
              </div>

              <div style={{ fontSize: '0.75rem', color: '#64748b', background: '#020617', padding: '0.5rem', borderRadius: '4px', fontFamily: 'monospace' }}>
                SQL: {chart.sql_query}
              </div>

              <ChartViewer spec={chart.chart_spec} sqlQuery={chart.sql_query} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
