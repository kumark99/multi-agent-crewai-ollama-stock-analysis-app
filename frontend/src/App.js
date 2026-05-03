import React, { useState, useCallback, useRef } from 'react';
import './App.css';

import Header from './components/Header';
import LLMConfig from './components/LLMConfig';
import StockInput from './components/StockInput';
import AgentFlowDiagram from './components/AgentFlowDiagram';
import ActivityLog from './components/ActivityLog';
import ReportViewer from './components/ReportViewer';

// ── Initial agent state ──────────────────────────────────────────────────────
const INITIAL_AGENTS = [
  {
    id: 1,
    name: 'Stock Analyst',
    role: 'Fundamental & Technical',
    icon: '📊',
    status: 'waiting',
  },
  {
    id: 2,
    name: 'News Researcher',
    role: 'News & Sentiment',
    icon: '📰',
    status: 'waiting',
  },
  {
    id: 3,
    name: 'Investment Strategist',
    role: 'Report & Recommendations',
    icon: '🎯',
    status: 'waiting',
  },
];

export default function App() {
  // Config
  const [config, setConfig] = useState({
    ollamaUrl: localStorage.getItem('ollamaUrl') || 'http://localhost:11434',
    model: localStorage.getItem('llmModel') || 'llama3.2',
  });

  // Analysis state
  const [symbol, setSymbol] = useState('');
  const [analysisStatus, setAnalysisStatus] = useState('idle'); // idle | analyzing | complete | error
  const [agents, setAgents] = useState(INITIAL_AGENTS);
  const [logs, setLogs] = useState([]);
  const [reportUrl, setReportUrl] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [ollamaConnected, setOllamaConnected] = useState(null); // null=unknown

  const wsRef = useRef(null);

  // ── Config save ──────────────────────────────────────────────────────────
  const handleConfigChange = useCallback((key, value) => {
    setConfig(prev => {
      const next = { ...prev, [key]: value };
      localStorage.setItem('ollamaUrl', next.ollamaUrl);
      localStorage.setItem('llmModel', next.model);
      return next;
    });
  }, []);

  // ── Log helper ───────────────────────────────────────────────────────────
  const pushLog = useCallback((entry) => {
    setLogs(prev => [...prev, {
      id: Date.now() + Math.random(),
      time: new Date().toLocaleTimeString('en-US', { hour12: false }),
      ...entry,
    }]);
  }, []);

  // ── Update agent status ───────────────────────────────────────────────────
  const setAgentStatus = useCallback((agentId, status) => {
    setAgents(prev =>
      prev.map(a => (a.id === agentId ? { ...a, status } : a))
    );
  }, []);

  // ── WebSocket event handler ───────────────────────────────────────────────
  const handleWsMessage = useCallback((event) => {
    let msg;
    try { msg = JSON.parse(event.data); } catch { return; }

    const iconMap = {
      started:        '🚀',
      agent_start:    '🤖',
      tool_use:       '🔧',
      thinking:       '💭',
      task_complete:  '✅',
      generating_pdf: '📄',
      crew_complete:  '🎉',
      error:          '❌',
      step:           '⚙️',
    };

    pushLog({
      type: msg.type,
      icon: iconMap[msg.type] || '•',
      message: msg.message || msg.summary || '',
    });

    switch (msg.type) {
      case 'started':
        setAgents(INITIAL_AGENTS);
        setReportUrl(null);
        setAgentStatus(1, 'active');
        break;

      case 'agent_start':
        if (msg.agent_id) {
          // Mark previous agent complete, new one active
          setAgents(prev =>
            prev.map(a => {
              if (a.id === msg.agent_id) return { ...a, status: 'active' };
              if (a.id < msg.agent_id) return { ...a, status: 'complete' };
              return a;
            })
          );
        }
        break;

      case 'task_complete':
        if (msg.agent_id) setAgentStatus(msg.agent_id, 'complete');
        break;

      case 'crew_complete':
        setAgents(prev => prev.map(a => ({ ...a, status: 'complete' })));
        setReportUrl(msg.pdf_url);
        setSessionId(msg.session_id);
        setAnalysisStatus('complete');
        break;

      case 'error':
        setAgents(prev => prev.map(a =>
          a.status === 'active' ? { ...a, status: 'error' } : a
        ));
        setAnalysisStatus('error');
        break;

      default:
        break;
    }
  }, [pushLog, setAgentStatus]);

  // ── Start analysis ────────────────────────────────────────────────────────
  const handleAnalyze = useCallback((stockSymbol) => {
    if (!stockSymbol) return;

    // Reset state
    setLogs([]);
    setAgents(INITIAL_AGENTS);
    setReportUrl(null);
    setAnalysisStatus('analyzing');

    const sid = `session_${Date.now()}`;
    setSessionId(sid);

    const wsUrl = `${process.env.REACT_APP_WS_URL || 'ws://localhost:8000'}/ws/${sid}`;

    if (wsRef.current) wsRef.current.close();
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      wsRef.current.send(JSON.stringify({
        symbol: stockSymbol,
        llm_model: config.model,
        ollama_base_url: config.ollamaUrl,
      }));
    };

    wsRef.current.onmessage = handleWsMessage;

    wsRef.current.onerror = () => {
      pushLog({ type: 'error', icon: '❌', message: 'WebSocket connection error. Is the backend running?' });
      setAnalysisStatus('error');
    };

    wsRef.current.onclose = () => {
      if (analysisStatus === 'analyzing') {
        setAnalysisStatus(prev => prev === 'analyzing' ? 'error' : prev);
      }
    };
  }, [config, handleWsMessage, pushLog, analysisStatus]);

  // ── Stop / reset ──────────────────────────────────────────────────────────
  const handleReset = useCallback(() => {
    if (wsRef.current) wsRef.current.close();
    setAnalysisStatus('idle');
    setAgents(INITIAL_AGENTS);
    setLogs([]);
    setReportUrl(null);
    setSessionId(null);
  }, []);

  // ── Render ────────────────────────────────────────────────────────────────
  const isAnalyzing = analysisStatus === 'analyzing';
  const completedCount = agents.filter(a => a.status === 'complete').length;

  return (
    <div className="app-wrapper">
      <Header ollamaConnected={ollamaConnected} setOllamaConnected={setOllamaConnected} ollamaUrl={config.ollamaUrl} />

      <main className="container py-4" style={{ maxWidth: '1100px' }}>

        {/* ── Config + Input Row ─────────────────────────────────────────── */}
        <div className="row g-3 mb-4">
          <div className="col-lg-5">
            <LLMConfig config={config} onChange={handleConfigChange} />
          </div>
          <div className="col-lg-7">
            <StockInput
              onAnalyze={handleAnalyze}
              onReset={handleReset}
              isAnalyzing={isAnalyzing}
              symbol={symbol}
              setSymbol={setSymbol}
            />
          </div>
        </div>

        {/* ── Agent Flow Diagram ─────────────────────────────────────────── */}
        <div className="glass-card p-3 mb-3">
          <div className="section-title">
            <span>🔄</span> Agent Pipeline
            {isAnalyzing && (
              <span className="ms-auto d-flex align-items-center gap-2" style={{ fontSize: '0.75rem', color: 'var(--accent-light)' }}>
                <div className="spinner-accent" /> Processing
              </span>
            )}
            {analysisStatus === 'complete' && (
              <span className="ms-auto" style={{ fontSize: '0.75rem', color: 'var(--teal)' }}>
                ✅ All 3 agents complete
              </span>
            )}
          </div>

          <AgentFlowDiagram agents={agents} symbol={symbol} isAnalyzing={isAnalyzing} />

          {/* Progress bar */}
          {(isAnalyzing || analysisStatus === 'complete') && (
            <div className="progress-steps mt-3">
              {[0, 1, 2].map(i => (
                <div
                  key={i}
                  className={`progress-step ${completedCount > i ? 'done' : completedCount === i && isAnalyzing ? 'active' : ''}`}
                />
              ))}
            </div>
          )}
        </div>

        {/* ── Activity Log + Report ──────────────────────────────────────── */}
        <div className="row g-3">
          <div className={reportUrl ? 'col-lg-7' : 'col-12'}>
            <div className="glass-card p-3">
              <div className="section-title">
                <span>📡</span> Live Agent Activity
                {isAnalyzing && (
                  <span className="ms-2 typing-dots">
                    <span /><span /><span />
                  </span>
                )}
              </div>
              <ActivityLog logs={logs} isAnalyzing={isAnalyzing} />
            </div>
          </div>

          {reportUrl && (
            <div className="col-lg-5">
              <ReportViewer
                reportUrl={reportUrl}
                symbol={symbol}
                sessionId={sessionId}
                onReset={handleReset}
              />
            </div>
          )}
        </div>

      </main>
    </div>
  );
}
