import React, { useRef } from 'react';
import { FiSearch, FiX, FiTrendingUp } from 'react-icons/fi';

const POPULAR = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TCS.NS', 'RELIANCE.NS'];

export default function StockInput({ onAnalyze, onReset, isAnalyzing, symbol, setSymbol }) {
  const inputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (symbol.trim() && !isAnalyzing) {
      onAnalyze(symbol.trim().toUpperCase());
    }
  };

  const handleQuick = (s) => {
    setSymbol(s);
    if (!isAnalyzing) onAnalyze(s);
  };

  const handleClear = () => {
    setSymbol('');
    onReset();
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  return (
    <div className="glass-card p-3 h-100">
      <div className="section-title mb-3">
        <FiTrendingUp size={12} /> Stock Symbol
      </div>

      <form onSubmit={handleSubmit}>
        <div className="d-flex gap-2">
          <div className="stock-input-wrap flex-grow-1 position-relative">
            <FiSearch
              size={16}
              style={{
                position: 'absolute', left: 14, top: '50%',
                transform: 'translateY(-50%)',
                color: 'var(--text-muted)',
                pointerEvents: 'none',
              }}
            />
            <input
              ref={inputRef}
              type="text"
              className="form-control stock-input-field"
              style={{ paddingLeft: '2.6rem !important' }}
              value={symbol}
              onChange={e => setSymbol(e.target.value.toUpperCase())}
              placeholder="Enter ticker  e.g. AAPL"
              maxLength={12}
              disabled={isAnalyzing}
              autoComplete="off"
              spellCheck={false}
            />
            {symbol && !isAnalyzing && (
              <button
                type="button"
                className="btn p-0"
                style={{
                  position: 'absolute', right: 12, top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--text-muted)',
                  background: 'none', border: 'none',
                }}
                onClick={handleClear}
              >
                <FiX size={16} />
              </button>
            )}
          </div>

          <button
            type={isAnalyzing ? 'button' : 'submit'}
            className="btn-analyze"
            onClick={isAnalyzing ? onReset : undefined}
            disabled={!symbol.trim() && !isAnalyzing}
          >
            {isAnalyzing ? (
              <span className="d-flex align-items-center gap-2">
                <span className="spinner-accent" style={{ width: 16, height: 16, borderWidth: 2 }} />
                Stop
              </span>
            ) : (
              <span className="d-flex align-items-center gap-1">
                <FiSearch size={15} /> Analyse
              </span>
            )}
          </button>
        </div>
      </form>

      {/* Quick-pick chips */}
      <div className="mt-3">
        <div className="config-label mb-2">⚡ Quick Pick</div>
        <div className="d-flex flex-wrap gap-1">
          {POPULAR.map(s => (
            <button
              key={s}
              type="button"
              className={`btn btn-sm rounded-pill px-2 py-1 ${symbol === s ? 'active' : ''}`}
              style={{
                fontSize: '0.7rem',
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                background: symbol === s ? 'rgba(108,99,255,0.25)' : 'rgba(255,255,255,0.05)',
                border: `1px solid ${symbol === s ? 'rgba(108,99,255,0.5)' : 'rgba(255,255,255,0.1)'}`,
                color: symbol === s ? 'var(--accent-light)' : 'var(--text-muted)',
                transition: 'all 0.2s',
              }}
              onClick={() => handleQuick(s)}
              disabled={isAnalyzing}
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
