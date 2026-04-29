/**
 * API client for the Table Extraction backend.
 */

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';
const API_ROOT = API_BASE.replace(/\/api\/?$/, '');

export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Upload failed');
  }
  return response.json();
}

export async function getResults(jobId) {
  const response = await fetch(`${API_BASE}/results/${jobId}`);
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Failed to fetch results');
  }
  return response.json();
}

export async function editResults(jobId, edits) {
  const response = await fetch(`${API_BASE}/results/${jobId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ edits }),
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'Edit failed');
  }
  return response.json();
}

export function getCsvUrl(jobId, format = 'matrix') {
  return `${API_BASE}/results/${jobId}/csv?format=${encodeURIComponent(format)}`;
}

export function getCropsUrl(jobId) {
  return `${API_BASE}/results/${jobId}/crops`;
}

export function resolveApiUrl(path) {
  if (!path) return null;
  if (/^https?:\/\//.test(path)) return path;
  return `${API_ROOT}${path.startsWith('/') ? path : `/${path}`}`;
}

export async function getHealth() {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) throw new Error('Health check failed');
  return response.json();
}
