const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== 'undefined'
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : 'http://localhost:8000');

// Simple in-memory token store (can be wired to Supabase or your auth backend)
let accessToken = null;

export function setAccessToken(token) {
  accessToken = token || null;
}

async function request(method, path, body) {
  const headers = {
    'Content-Type': 'application/json',
  };
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API ${method} ${path} failed: ${res.status} ${text}`);
  }

  const ct = res.headers.get('Content-Type') || '';
  if (ct.includes('application/json')) {
    return res.json();
  }
  return res.text();
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, body),
  del: (path, body) => request('DELETE', path, body),
};

