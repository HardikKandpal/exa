import React, { useState, useEffect } from 'react';
import DataTable from './DataTable';

export default function AnalyticsOverview() {
  const [activeTab, setActiveTab] = useState('channel-activity');
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadData = async (endpoint) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/analytics/${endpoint}`);
      const json = await res.json();
      if (json.success) {
        setData(json.data || []);
      }
    } catch (err) {
      console.error('Analytics load error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(activeTab);
  }, [activeTab]);

  return (
    <div style={{ padding: '2rem', width: '100%', height: '100%', overflowY: 'auto' }}>
      <h2 style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.5rem', color: '#f8fafc' }}>
        Database Aggregate Metrics
      </h2>
      <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
        Time-series aggregates computed directly in PostgreSQL via optimized SQL queries.
      </p>

      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <button
          className={`nav-tab ${activeTab === 'channel-activity' ? 'active' : ''}`}
          onClick={() => setActiveTab('channel-activity')}
        >
          📊 Channel Activity
        </button>
        <button
          className={`nav-tab ${activeTab === 'member-growth' ? 'active' : ''}`}
          onClick={() => setActiveTab('member-growth')}
        >
          📈 Member Growth
        </button>
        <button
          className={`nav-tab ${activeTab === 'hourly-distribution' ? 'active' : ''}`}
          onClick={() => setActiveTab('hourly-distribution')}
        >
          ⏰ Hourly Distribution
        </button>
      </div>

      {loading ? (
        <div style={{ color: '#94a3b8' }}>Computing aggregate metrics in database...</div>
      ) : (
        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <DataTable data={data} />
        </div>
      )}
    </div>
  );
}
