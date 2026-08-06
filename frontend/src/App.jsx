import React, { useState } from 'react';
import ChatInterface from './components/ChatInterface';
import Dashboard from './components/Dashboard';
import AnalyticsOverview from './components/AnalyticsOverview';
import { MessageSquare, LayoutDashboard, BarChart3 } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');

  return (
    <div className="app-container">
      <header className="navbar">
        <div className="brand">
          <MessageSquare className="w-6 h-6 text-sky-400" />
          <span>Exaqube Discord Analytics</span>
        </div>

        <nav className="nav-tabs">
          <button
            className={`nav-tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            💬 Conversational AI Agent
          </button>
          <button
            className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            📌 Pinned Dashboard
          </button>
          <button
            className={`nav-tab ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            📊 Time-Series Aggregates
          </button>
        </nav>
      </header>

      <main className="main-content">
        {activeTab === 'chat' && <ChatInterface />}
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'analytics' && <AnalyticsOverview />}
      </main>
    </div>
  );
}
