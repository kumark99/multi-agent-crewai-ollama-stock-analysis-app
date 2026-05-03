const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * Fetch available Ollama models from the backend.
 * @param {string} ollamaUrl - Ollama base URL
 * @returns {Promise<{ models: string[], connected: boolean }>}
 */
export async function fetchModels(ollamaUrl = 'http://localhost:11434') {
  const res = await fetch(
    `${API_BASE}/api/models?base_url=${encodeURIComponent(ollamaUrl)}`
  );
  return res.json();
}

/**
 * Check if the backend API is healthy.
 * @returns {Promise<boolean>}
 */
export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Get the download URL for a generated report.
 * @param {string} sessionId
 * @returns {string}
 */
export function getReportUrl(sessionId) {
  return `${API_BASE}/api/report/${sessionId}`;
}
