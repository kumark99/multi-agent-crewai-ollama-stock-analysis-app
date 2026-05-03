import React from 'react';
import { FiDownload, FiRotateCcw, FiCheckCircle, FiFileText } from 'react-icons/fi';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function ReportViewer({ reportUrl, symbol, sessionId, onReset }) {
  const downloadUrl = reportUrl
    ? `${API_URL}${reportUrl}`
    : null;

  return (
    <div className="report-complete-card h-100 d-flex flex-column">

      {/* Success icon */}
      <div className="success-icon">🎉</div>

      <h5 className="mb-1" style={{ color: 'var(--teal)', fontWeight: 700 }}>
        Analysis Complete!
      </h5>
      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
        Your comprehensive <strong style={{ color: 'var(--text-primary)' }}>{symbol}</strong> investment
        report with fundamental analysis, technical indicators, news, and recommendations is ready.
      </p>

      {/* Stats row */}
      <div className="d-flex justify-content-center gap-3 mb-4">
        {[
          { icon: '📊', label: 'Fundamental', sub: 'Analysis' },
          { icon: '📈', label: 'Technical',   sub: 'Indicators' },
          { icon: '📰', label: 'News',         sub: 'Research' },
          { icon: '🎯', label: 'Recommendation', sub: 'Report' },
        ].map(stat => (
          <div key={stat.label} className="text-center" style={{ minWidth: 56 }}>
            <div style={{ fontSize: '1.4rem', marginBottom: 2 }}>{stat.icon}</div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', fontWeight: 600, lineHeight: 1.2 }}>
              {stat.label}<br />{stat.sub}
            </div>
          </div>
        ))}
      </div>

      {/* Download button */}
      {downloadUrl && (
        <a
          href={downloadUrl}
          download={`${symbol}_analysis_report.pdf`}
          className="btn-download d-flex align-items-center justify-content-center gap-2 text-decoration-none mb-3"
          style={{ borderRadius: 12, padding: '0.75rem 1.75rem', fontWeight: 700, color: '#fff', width: '100%' }}
        >
          <FiDownload size={18} />
          Download PDF Report
        </a>
      )}

      {/* View online (open in new tab) */}
      {downloadUrl && (
        <a
          href={downloadUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="btn d-flex align-items-center justify-content-center gap-2 mb-3"
          style={{
            background: 'rgba(108,99,255,0.15)',
            border: '1px solid rgba(108,99,255,0.3)',
            color: 'var(--accent-light)',
            borderRadius: 12,
            fontWeight: 600,
            fontSize: '0.9rem',
            textDecoration: 'none',
          }}
        >
          <FiFileText size={16} />
          View in Browser
        </a>
      )}

      {/* New analysis */}
      <button
        className="btn d-flex align-items-center justify-content-center gap-2"
        style={{
          background: 'transparent',
          border: '1px solid var(--border)',
          color: 'var(--text-secondary)',
          borderRadius: 12,
          fontWeight: 600,
          fontSize: '0.85rem',
          marginTop: 'auto',
        }}
        onClick={onReset}
      >
        <FiRotateCcw size={14} />
        New Analysis
      </button>

    </div>
  );
}
