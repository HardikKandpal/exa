import React, { useState, useRef, useEffect } from 'react';
import DataTable from './DataTable';
import ChartViewer from './ChartViewer';

function FormattedMessage({ text }) {
  if (!text) return null;

  const lines = text.split('\n');
  const blocks = [];
  let currentTable = null;
  let currentParagraph = [];

  const flushParagraph = () => {
    if (currentParagraph.length > 0) {
      const content = currentParagraph.join('\n').trim();
      if (content) {
        blocks.push({ type: 'p', content });
      }
      currentParagraph = [];
    }
  };

  const flushTable = () => {
    if (currentTable && currentTable.length > 0) {
      blocks.push({ type: 'table', rows: currentTable });
      currentTable = null;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.startsWith('|') && line.endsWith('|')) {
      flushParagraph();
      const cells = line
        .split('|')
        .map((c) => c.trim())
        .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);

      if (cells.every((c) => /^:?-+:?$/.test(c))) {
        continue;
      }
      if (!currentTable) currentTable = [];
      currentTable.push(cells);
    } else {
      flushTable();
      currentParagraph.push(lines[i]);
    }
  }
  flushParagraph();
  flushTable();

  return (
    <div className="formatted-message">
      {blocks.map((block, idx) => {
        if (block.type === 'table') {
          const header = block.rows[0];
          const body = block.rows.slice(1);
          return (
            <div key={idx} style={{ margin: '0.75rem 0', overflowX: 'auto' }}>
              <table className="data-table">
                {header && (
                  <thead>
                    <tr>
                      {header.map((cell, cIdx) => (
                        <th key={cIdx}>{cell}</th>
                      ))}
                    </tr>
                  </thead>
                )}
                <tbody>
                  {body.map((row, rIdx) => (
                    <tr key={rIdx}>
                      {row.map((cell, cIdx) => (
                        <td key={cIdx}>{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        return (
          <p key={idx} style={{ marginBottom: '0.5rem', whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>
            {block.content}
          </p>
        );
      })}
    </div>
  );
}

export default function ChatInterface() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'agent',
      text: 'Hello! I am your Discord Analytics AI Agent. Ask me questions about member growth, server activity, or ask me to generate charts, Excel workbooks, or PowerPoint presentation decks!',
      stages: []
    }
  ]);
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e) => {
    e?.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userText = input.trim();
    setInput('');
    const userMsg = { id: Date.now().toString(), sender: 'user', text: userText };

    const agentMsgId = (Date.now() + 1).toString();
    const agentMsg = {
      id: agentMsgId,
      sender: 'agent',
      text: '',
      stages: [],
      artifacts: [],
      data: null,
      chartSpec: null,
      lastSql: null
    };

    const history = messages
      .filter((m) => m.text && m.id !== 'welcome')
      .map((m) => ({
        role: m.sender === 'user' ? 'user' : 'assistant',
        content: m.text
      }));

    setMessages((prev) => [...prev, userMsg, agentMsg]);
    setIsStreaming(true);

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText, history })
      });

      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const payload = JSON.parse(line.slice(6));
              const eventStage = payload.stage;

              setMessages((prev) =>
                prev.map((msg) => {
                  if (msg.id !== agentMsgId) return msg;

                  const updatedStages = [...msg.stages, payload];
                  let updatedText = msg.text;
                  let updatedData = msg.data;
                  let updatedChartSpec = msg.chartSpec;
                  let updatedArtifacts = [...(msg.artifacts || [])];
                  let updatedLastSql = msg.lastSql;

                  if (eventStage === 'final_answer') {
                    updatedText = payload.content;
                  } else if (eventStage === 'tool_result') {
                    if (payload.plugin === 'query') {
                      updatedData = payload.result;
                      updatedLastSql = payload.metadata?.sql;
                    } else if (payload.plugin === 'chart') {
                      updatedChartSpec = payload.result;
                    }
                    if (payload.artifact_url) {
                      updatedArtifacts.push({
                        id: payload.artifact_id,
                        url: payload.artifact_url,
                        type: payload.output_type,
                        plugin: payload.plugin
                      });
                    }
                  }

                  return {
                    ...msg,
                    text: updatedText,
                    stages: updatedStages,
                    data: updatedData,
                    chartSpec: updatedChartSpec,
                    artifacts: updatedArtifacts,
                    lastSql: updatedLastSql
                  };
                })
              );
            } catch (err) {
              console.error('Failed to parse SSE payload:', err);
            }
          }
        }
      }
    } catch (err) {
      console.error('Error during SSE stream:', err);
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="chat-layout">
      <div className="chat-panel">
        <div className="messages-list">
          {messages.map((msg) => (
            <div key={msg.id} className={`chat-bubble ${msg.sender}`}>
              {msg.sender === 'agent' && msg.stages && msg.stages.length > 0 && (
                <div style={{ marginBottom: '0.75rem' }}>
                  {msg.stages.map((stg, i) => (
                    <div key={i} className={`stage-badge stage-${stg.stage}`}>
                      ● Stage: {stg.stage?.toUpperCase()} {stg.plugin ? `[${stg.plugin}]` : ''}{' '}
                      {stg.stage !== 'final_answer' && stg.content ? `- ${stg.content}` : ''}
                      {stg.progress ? `- ${stg.progress}` : ''}
                    </div>
                  ))}
                </div>
              )}

              {msg.text ? (
                <FormattedMessage text={msg.text} />
              ) : (
                isStreaming && msg.sender === 'agent' && <div>Reasoning & processing...</div>
              )}

              {msg.artifacts && msg.artifacts.length > 0 && (
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.75rem' }}>
                  {msg.artifacts.map((art) => (
                    <a key={art.id} href={art.url} download className="artifact-btn">
                      📥 Download {art.plugin.toUpperCase()} ({art.type})
                    </a>
                  ))}
                </div>
              )}

              {msg.chartSpec && (
                <ChartViewer spec={msg.chartSpec} artifactUrl={msg.artifacts?.find((a) => a.plugin === 'chart')?.url} sqlQuery={msg.lastSql} />
              )}

              {msg.data && msg.data.length > 0 && (
                <div style={{ marginTop: '1rem' }}>
                  <h5 style={{ color: '#94a3b8', fontSize: '0.8rem', marginBottom: '0.5rem' }}>SQL Result Preview ({msg.data.length} rows)</h5>
                  <DataTable data={msg.data.slice(0, 5)} />
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSend} className="chat-input-bar">
          <input
            type="text"
            className="chat-input"
            placeholder="Ask a question (e.g. 'Chart message volume per channel, then put it in a deck')..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isStreaming}
          />
          <button type="submit" className="btn-send" disabled={isStreaming}>
            {isStreaming ? 'Streaming...' : 'Send'}
          </button>
        </form>
      </div>
    </div>
  );
}
