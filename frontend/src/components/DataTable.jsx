import React from 'react';

export default function DataTable({ data }) {
  if (!data || data.length === 0) {
    return <div style={{ padding: '1rem', color: '#94a3b8', fontSize: '0.85rem' }}>No tabular data available.</div>;
  }

  const columns = Object.keys(data[0]);

  return (
    <div className="data-table-container">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr key={idx}>
              {columns.map((col) => (
                <td key={col}>{row[col] !== null ? String(row[col]) : '-'}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
