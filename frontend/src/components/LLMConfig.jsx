import React, { useEffect, useState } from 'react';
import { FiCpu, FiLink, FiRefreshCw, FiChevronDown } from 'react-icons/fi';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function LLMConfig({ config, onChange }) {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchModels = async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/api/models?base_url=${encodeURIComponent(config.ollamaUrl)}`
      );
      const data = await res.json();
      if (data.models && data.models.length > 0) {
        setModels(data.models);
        // Auto-select first model if current not in list
        if (!data.models.includes(config.model)) {
          onChange('model', data.models[0]);
        }
      }
    } catch {
      setModels(['llama3.2', 'llama3.1', 'mistral', 'gemma2', 'codellama', 'phi3']);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="config-panel h-100">
      <div className="section-title mb-3">
        <FiCpu size={12} /> LLM Configuration
      </div>

      {/* Ollama URL */}
      <div className="mb-3">
        <div className="config-label d-flex align-items-center gap-1">
          <FiLink size={11} /> Ollama Base URL
        </div>
        <input
          type="text"
          className="form-control config-input"
          value={config.ollamaUrl}
          onChange={e => onChange('ollamaUrl', e.target.value)}
          onBlur={fetchModels}
          placeholder="http://localhost:11434"
        />
      </div>

      {/* Model Select */}
      <div>
        <div className="config-label d-flex align-items-center justify-content-between">
          <span>🧠 LLM Model</span>
          <button
            className="btn btn-sm p-0 d-flex align-items-center gap-1"
            style={{ fontSize: '0.7rem', color: 'var(--accent-light)', background: 'none', border: 'none' }}
            onClick={fetchModels}
            disabled={loading}
          >
            <FiRefreshCw size={11} className={loading ? 'spin' : ''} />
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
        <select
          className="form-select config-select"
          value={config.model}
          onChange={e => onChange('model', e.target.value)}
        >
          {models.length === 0
            ? ['llama3.2', 'llama3.1', 'mistral', 'gemma2', 'codellama', 'phi3'].map(m => (
                <option key={m} value={m}>{m}</option>
              ))
            : models.map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
        </select>
      </div>

      {/* Active model badge */}
      <div className="mt-2 d-flex align-items-center gap-2">
        <span
          className="px-2 py-1 rounded"
          style={{
            background: 'rgba(108,99,255,0.15)',
            border: '1px solid rgba(108,99,255,0.3)',
            fontSize: '0.7rem',
            color: 'var(--accent-light)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          🔵 {config.model}
        </span>
        <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>active model</span>
      </div>
    </div>
  );
}
