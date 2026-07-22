const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const HISTORY_KEY = 'verisight.scan-history.v2';

async function parseResponse(response) {
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const message = payload?.detail || payload?.message || `Request failed (${response.status})`;
    throw new Error(typeof message === 'string' ? message : 'Analysis failed.');
  }
  return payload;
}

export async function getHealth() {
  const response = await fetch(`${API_BASE}/api/health`, {
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  });
  return parseResponse(response);
}

export async function analyzeMedia(file, mediaType, onProgress) {
  const form = new FormData();
  form.append('file', file);
  onProgress?.(18);
  const endpoint = mediaType === 'video' ? '/api/analyze/video' : '/api/analyze/image';
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    body: form,
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  });
  onProgress?.(94);
  return parseResponse(response);
}

export function formatBytes(bytes = 0) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / (1024 ** index);
  return `${value >= 10 || index === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[index]}`;
}

export function formatTime(seconds = 0) {
  const safe = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(safe / 60);
  const remainder = Math.floor(safe % 60);
  return `${minutes}:${String(remainder).padStart(2, '0')}`;
}

export function riskColor(value = 0) {
  if (value >= 67) return '#ff4f91';
  if (value >= 35) return '#ffb648';
  return '#4ef5a0';
}

export function loadHistory() {
  try {
    const value = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export function saveHistory(history) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 20)));
  } catch {
    // Storage can be disabled; scans still work without local history.
  }
}

export function historyRecord(result, file) {
  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    filename: file.name,
    size: file.size,
    mediaType: result.media_type || (file.type.startsWith('video/') ? 'video' : 'image'),
    authenticity: result.authenticity_score,
    synthetic: result.synthetic_probability,
    verdict: result.verdict,
    detectorMode: result.model?.mode || 'Forensic engine',
    createdAt: new Date().toISOString(),
  };
}

function safeName(name) {
  return String(name || 'verisight-report').replace(/[^a-z0-9._-]+/gi, '-').replace(/^-+|-+$/g, '');
}

export function downloadJson(result) {
  if (!result) return;
  const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${safeName(result.filename)}-verisight.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function downloadReportCard(result) {
  if (!result) return;
  const canvas = document.createElement('canvas');
  canvas.width = 1200;
  canvas.height = 675;
  const context = canvas.getContext('2d');
  const gradient = context.createLinearGradient(0, 0, canvas.width, canvas.height);
  gradient.addColorStop(0, '#050914');
  gradient.addColorStop(.55, '#0c1730');
  gradient.addColorStop(1, '#27051e');
  context.fillStyle = gradient;
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.strokeStyle = '#25e4ff';
  context.lineWidth = 3;
  context.strokeRect(34, 34, canvas.width - 68, canvas.height - 68);
  context.fillStyle = '#ecf6ff';
  context.font = '800 58px Arial';
  context.fillText('VERISIGHT', 76, 112);
  context.fillStyle = '#8ea3c3';
  context.font = '600 24px Arial';
  context.fillText('AI, DEEPFAKE & FILTER DETECTION REPORT', 76, 150);
  context.fillStyle = '#ffffff';
  context.font = '800 108px Arial';
  context.fillText(`${result.authenticity_score}%`, 76, 310);
  context.fillStyle = '#55eea1';
  context.font = '800 34px Arial';
  context.fillText('AUTHENTICITY SCORE', 82, 355);
  context.fillStyle = '#ffffff';
  context.font = '800 36px Arial';
  context.fillText(result.verdict || 'Screening complete', 520, 250);
  context.fillStyle = '#a6b6ce';
  context.font = '24px Arial';
  const lines = [
    `Synthetic: ${result.synthetic_probability}%`,
    `Deepfake: ${result.deepfake_probability}%`,
    `Filters: ${result.filter_probability}%`,
    `Confidence: ${result.confidence}%`,
  ];
  lines.forEach((line, index) => context.fillText(line, 520, 305 + index * 48));
  context.fillStyle = '#7287a8';
  context.font = '20px Arial';
  context.fillText('Probabilistic screening — not proof and not a sole basis for accusation.', 76, 590);
  canvas.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${safeName(result.filename)}-verisight-card.png`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, 'image/png');
}
