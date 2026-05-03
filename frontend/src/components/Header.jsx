import React, { useEffect, useState } from 'react';
import { FiBrainCircuit } from 'react-icons/fi';
import { FaCircle, FaRobot } from 'react-icons/fa';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function Header({ ollamaConnected, setOllamaConnected, ollamaUrl }) {
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    const check = async () => {
      setChecking(true);
      try {
        const res = await fetch(`${API_URL}/api/models?base_url=${encodeURIComponent(ollamaUrl)}`);
        const data = await res.json();
        setOllamaConnected(data.connected !== false);
      } catch {
        setOllamaConnected(false);
      } finally {
        setChecking(false);
      }
    };

    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, [ollamaUrl, setOllamaConnected]);

  const statusLabel = checking
    ? 'Checking…'
    : ollamaConnected
    ? 'Ollama Connected'
    : 'Ollama Offline';

  const dotClass = checking ? 'checking' : ollamaConnected ? 'connected' : 'disconnected';

  return (
    <header className="site-header">
      <div className="container d-flex align-items-center justify-content-between" style={{ maxWidth: '1100px' }}>

        {/* Brand */}
        <div className="d-flex align-items-center gap-2">
          <div
            className="d-flex align-items-center justify-content-center rounded-3"
            style={{
              width: 38, height: 38,
              background: 'linear-gradient(135deg, rgba(108,99,255,0.3), rgba(0,201,167,0.3))',
              border: '1px solid rgba(108,99,255,0.4)',
              fontSize: '1.1rem',
            }}
          >
            🤖
          </div>
          <div>
            <div className="brand-logo">StockMind AI</div>
            <div className="brand-tagline">Multi-Agent Stock Analysis · Powered by CrewAI + Ollama</div>
          </div>
        </div>

        {/* Ollama status */}
        <div className="d-flex align-items-center gap-3">
          <div
            className="d-flex align-items-center gap-1 px-3 py-1 rounded-pill"
            style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              fontSize: '0.78rem',
              color: 'var(--text-secondary)',
            }}
          >
            <span className={`status-dot ${dotClass}`} />
            {statusLabel}
          </div>

          <div
            className="d-none d-md-flex align-items-center gap-1 px-3 py-1 rounded-pill"
            style={{
              background: 'rgba(108,99,255,0.1)',
              border: '1px solid rgba(108,99,255,0.25)',
              fontSize: '0.73rem',
              color: 'var(--accent-light)',
            }}
          >
            <FaRobot size={11} style={{ marginRight: 4 }} />
            CrewAI · 3 Agents
          </div>
        </div>

      </div>
    </header>
  );
}
