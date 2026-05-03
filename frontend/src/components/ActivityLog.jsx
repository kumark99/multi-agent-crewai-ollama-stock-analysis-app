import React, { useEffect, useRef } from 'react';

const TYPE_META = {
  started:        { icon: '🚀', color: '#8b85ff' },
  agent_start:    { icon: '🤖', color: '#ffd166' },
  tool_use:       { icon: '🔧', color: '#8892b0' },
  thinking:       { icon: '💭', color: '#5a6380' },
  task_complete:  { icon: '✅', color: '#00c9a7' },
  generating_pdf: { icon: '📄', color: '#8b85ff' },
  crew_complete:  { icon: '🎉', color: '#00c9a7' },
  error:          { icon: '❌', color: '#ef476f' },
  step:           { icon: '⚙️', color: '#5a6380' },
};

const EMPTY_PLACEHOLDER = [
  { id: 'p1', type: 'placeholder', icon: '📊', message: 'Enter a stock symbol and click Analyse to begin…', time: '' },
  { id: 'p2', type: 'placeholder', icon: '🤖', message: 'Agent 1 will perform fundamental & technical analysis', time: '' },
  { id: 'p3', type: 'placeholder', icon: '📰', message: 'Agent 2 will research latest news & market sentiment', time: '' },
  { id: 'p4', type: 'placeholder', icon: '📋', message: 'Agent 3 will generate a comprehensive PDF report', time: '' },
];

export default function ActivityLog({ logs, isAnalyzing }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const displayLogs = logs.length === 0 ? EMPTY_PLACEHOLDER : logs;

  return (
    <div className="activity-log">
      {displayLogs.map(entry => {
        const meta = TYPE_META[entry.type] || { icon: '•', color: 'var(--text-muted)' };
        const isPlaceholder = entry.type === 'placeholder';

        return (
          <div
            key={entry.id}
            className={`log-entry ${entry.type}`}
            style={{ opacity: isPlaceholder ? 0.45 : 1 }}
          >
            {/* Time */}
            {entry.time ? (
              <span className="log-time">{entry.time}</span>
            ) : (
              <span className="log-time" style={{ minWidth: 56 }} />
            )}

            {/* Icon */}
            <span className="log-icon">{entry.icon || meta.icon}</span>

            {/* Message */}
            <span
              className="log-message"
              style={{ color: isPlaceholder ? 'var(--text-muted)' : meta.color }}
            >
              {entry.message}
            </span>
          </div>
        );
      })}

      {/* Typing indicator when analyzing */}
      {isAnalyzing && (
        <div className="log-entry" style={{ paddingTop: 4 }}>
          <span className="log-time" />
          <span className="log-icon">💭</span>
          <span className="log-message d-flex align-items-center gap-2" style={{ color: 'var(--text-muted)' }}>
            <span>Agents processing</span>
            <span className="typing-dots">
              <span /><span /><span />
            </span>
          </span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
