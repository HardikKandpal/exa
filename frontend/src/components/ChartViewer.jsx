import React, { useState } from 'react';

export default function ChartViewer({ spec, artifactUrl, sqlQuery, onPin }) {
  const [pinned, setPinned] = useState(false);

  if (!spec && !artifactUrl) return null;

  const handlePin = async () => {
    if (!spec) return;
    try {
      const res = await fetch('/api/pinned-charts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: spec.title || 'Pinned Analytics Chart',
          chart_type: spec.chart_type || 'bar',
          sql_query: sqlQuery || spec.sql || 'SELECT 1;',
          chart_spec: spec
        })
      });
      const data = await res.json();
      if (data.success) {
        setPinned(true);
        if (onPin) onPin(data.data);
      }
    } catch (err) {
      console.error('Failed to pin chart:', err);
    }
  };

  return (
    <div className="glass-card" style={{ padding: '1.25rem', marginTop: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h4 style={{ color: '#38bdf8', fontSize: '1rem', fontWeight: '600' }}>{spec?.title || 'Generated Visualization'}</h4>
        {spec && (
          <button 
            className="artifact-btn" 
            onClick={handlePin}
            style={{ 
              background: pinned ? 'rgba(52, 211, 153, 0.2)' : 'rgba(56, 189, 248, 0.15)',
              borderColor: pinned ? 'rgba(52, 211, 153, 0.4)' : 'rgba(56, 189, 248, 0.3)',
              color: pinned ? '#34d399' : '#38bdf8'
            }}
          >
            {pinned ? '📌 Pinned to Dashboard' : '📌 Pin to Dashboard'}
          </button>
        )}
      </div>

      {artifactUrl ? (
        <img 
          src={artifactUrl} 
          alt={spec?.title || 'Chart'} 
          style={{ width: '100%', height: 'auto', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }} 
        />
      ) : (
        <div style={{ padding: '1rem', background: '#1e293b', borderRadius: '8px', textAlign: 'center', color: '#94a3b8' }}>
          Chart Spec Generated ({spec?.chart_type?.toUpperCase()}) - {spec?.data?.length || 0} rows
        </div>
      )}
    </div>
  );
}
