'use client';

// Lightweight client-side auth helpers.
// Token + user are cached in localStorage so the session survives a refresh.
// The token itself is verified server-side on every protected request.

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';

const TOKEN_KEY = 'agri_auth_token';
const USER_KEY = 'agri_auth_user';

export function getToken() {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser() {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveSession(token, user) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  // Let other tabs/components know the session changed.
  window.dispatchEvent(new Event('agri-auth-change'));
}

export function clearSession() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  window.dispatchEvent(new Event('agri-auth-change'));
}

// Wrapper around fetch that attaches the Bearer token and, on a 401
// (expired/invalid session), clears the session automatically.
export async function authFetch(url, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    clearSession();
  }
  return res;
}

// Hook used by protected pages: returns { user, loading }.
// Redirects to /login if there is no valid session.
export function useAuth({ redirectIfUnauthenticated = true } = {}) {
  const router = useRouter();
  const [user, setUser] = useState(() => getStoredUser());
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      if (redirectIfUnauthenticated) router.replace('/login');
      return;
    }
    try {
      const res = await authFetch('/api/auth/me');
      if (!res.ok) throw new Error('unauthenticated');
      const me = await res.json();
      setUser(me);
      localStorage.setItem(USER_KEY, JSON.stringify(me));
    } catch {
      clearSession();
      setUser(null);
      if (redirectIfUnauthenticated) router.replace('/login');
    } finally {
      setLoading(false);
    }
  }, [router, redirectIfUnauthenticated]);

  useEffect(() => {
    refresh();
    window.addEventListener('agri-auth-change', refresh);
    return () => window.removeEventListener('agri-auth-change', refresh);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const logout = useCallback(() => {
    clearSession();
    router.replace('/login');
  }, [router]);

  return { user, loading, logout, refresh };
}
