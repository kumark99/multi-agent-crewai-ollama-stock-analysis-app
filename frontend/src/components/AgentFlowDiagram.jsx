import React from 'react';

const AGENT_COLORS = {
  waiting:  { border: '#4a4f6a', bg: 'transparent', glow: 'none' },
  active:   { border: '#6c63ff', bg: 'rgba(108,99,255,0.08)', glow: '0 0 0 4px rgba(108,99,255,0.2)' },
  complete: { border: '#00c9a7', bg: 'rgba(0,201,167,0.08)',  glow: '0 0 12px rgba(0,201,167,0.2)' },
  error:    { border: '#ef476f', bg: 'rgba(239,71,111,0.08)', glow: '0 0 12px rgba(239,71,111,0.2)' },
};

function AgentNode({ agent, isActive }) {
  const colors = AGENT_COLORS[agent.status] || AGENT_COLORS.waiting;

  return (
    <div className="flow-node">
      {/* Icon circle */}
      <div
        className={`agent-icon-wrap ${agent.status}`}
        style={{
          background: colors.bg,
          borderColor: colors.border,
          boxShadow: colors.glow,
        }}
      >
        <span role="img" aria-label={agent.name}>{agent.icon}</span>

        {/* Completion checkmark overlay */}
        {agent.status === 'complete' && (
          <div
            style={{
              position: 'absolute',
              bottom: -4, right: -4,
              width: 20, height: 20,
              borderRadius: '50%',
              background: '#00c9a7',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '0.65rem',
              color: '#fff',
              fontWeight: 700,
              border: '2px solid var(--bg-card)',
              animation: 'bounce-in 0.4s ease',
            }}
          >
            ✓
          </div>
        )}

        {/* Error X overlay */}
        {agent.status === 'error' && (
          <div
            style={{
              position: 'absolute',
              bottom: -4, right: -4,
              width: 20, height: 20,
              borderRadius: '50%',
              background: '#ef476f',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '0.65rem',
              color: '#fff',
              fontWeight: 700,
              border: '2px solid var(--bg-card)',
            }}
          >
            ✕
          </div>
        )}
      </div>

      {/* Labels */}
      <div className="agent-node-label">
        <div className="agent-name">{agent.name}</div>
        <div className="agent-role">{agent.role}</div>
      </div>

      {/* Status badge */}
      <span className={`agent-status-badge ${agent.status}`}>
        {agent.status === 'active' && '● '}
        {agent.status === 'complete' && '✓ '}
        {agent.status === 'error' && '✕ '}
        {agent.status.charAt(0).toUpperCase() + agent.status.slice(1)}
      </span>
    </div>
  );
}

function Connector({ animated }) {
  return (
    <div className="flow-connector">
      <div className={`flow-arrow-line ${animated ? 'animated' : ''}`} />
    </div>
  );
}

export default function AgentFlowDiagram({ agents, symbol, isAnalyzing }) {
  const activeAgent = agents.find(a => a.status === 'active');

  return (
    <div>
      {/* Active agent info strip */}
      {activeAgent && isAnalyzing && (
        <div
          className="mb-3 px-3 py-2 rounded-3 d-flex align-items-center gap-2"
          style={{
            background: 'rgba(108,99,255,0.1)',
            border: '1px solid rgba(108,99,255,0.25)',
            fontSize: '0.8rem',
            color: 'var(--accent-light)',
          }}
        >
          <span className="spinner-accent" style={{ width: 14, height: 14, borderWidth: 2 }} />
          <strong>Agent {activeAgent.id}</strong> – {activeAgent.name} is working on{' '}
          <strong>{symbol}</strong> analysis…
        </div>
      )}

      {/* Flow diagram */}
      <div className="flow-container">

        {/* Input node */}
        <div className="flow-endpoint input">
          <div className="endpoint-icon">📥</div>
          <div className="endpoint-label">Input<br />{symbol || '—'}</div>
        </div>

        <Connector animated={agents[0].status === 'active' || agents[0].status === 'complete'} />

        {/* Agent 1 */}
        <AgentNode agent={agents[0]} />

        <Connector animated={agents[1].status === 'active' || agents[1].status === 'complete'} />

        {/* Agent 2 */}
        <AgentNode agent={agents[1]} />

        <Connector animated={agents[2].status === 'active' || agents[2].status === 'complete'} />

        {/* Agent 3 */}
        <AgentNode agent={agents[2]} />

        <Connector animated={agents[2].status === 'complete'} />

        {/* Output node */}
        <div className="flow-endpoint output">
          <div
            className="endpoint-icon"
            style={agents[2].status === 'complete' ? { animation: 'bounce-in 0.5s ease' } : {}}
          >
            📑
          </div>
          <div className="endpoint-label">PDF<br />Report</div>
        </div>

      </div>
    </div>
  );
}
