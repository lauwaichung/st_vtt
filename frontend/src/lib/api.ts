import { app } from './state.svelte';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}

async function call<T>(method: string, url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: 'same-origin',
  });
  if (!res.ok) {
    if (res.status === 401 && !url.endsWith('/api/login') && app.me) {
      app.loginNotice = 'Your session ended. You may have signed in on another device.';
      app.me = null;
    }
    let detail = res.statusText;
    try { const j = await res.json(); detail = j.detail ?? j.error ?? detail; } catch {}
    throw new ApiError(res.status, typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(url: string) => call<T>('GET', url),
  post: <T>(url: string, body?: unknown) => call<T>('POST', url, body ?? {}),
  del: <T>(url: string) => call<T>('DELETE', url),
};
