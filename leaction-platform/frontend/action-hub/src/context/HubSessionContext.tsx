'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import axios from 'axios';
import { getHubApiBase } from '@/lib/hub-api';

const HUB_SESSION_KEY = 'actionhub_session';

export type HubUser = {
  id: string;
  email: string;
  name: string;
};

type HubSessionState = {
  user: HubUser | null;
  token: string | null;
  hydrated: boolean;
  login: (email: string, password: string) => Promise<HubUser>;
  logout: () => void;
  /** Define sessão a partir de e-mail já conhecido (ex.: URL ?email=). */
  adoptEmail: (email: string) => void;
};

type StoredSession = {
  user: HubUser;
  token?: string | null;
};

const HubSessionContext = createContext<HubSessionState | undefined>(undefined);

function readStoredSession(): StoredSession | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(HUB_SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredSession;
    if (!parsed?.user?.email) return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeStoredSession(session: StoredSession | null) {
  if (typeof window === 'undefined') return;
  try {
    if (!session) {
      localStorage.removeItem(HUB_SESSION_KEY);
      return;
    }
    localStorage.setItem(HUB_SESSION_KEY, JSON.stringify(session));
  } catch {
    /* ignore quota */
  }
}

export function HubSessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<HubUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const stored = readStoredSession();
    if (stored) {
      setUser(stored.user);
      setToken(stored.token || null);
    }
    setHydrated(true);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const apiBase = getHubApiBase();
    try {
      const { data } = await axios.post(
        `${apiBase}/auth/login`,
        { email: email.trim(), password },
        { timeout: 15000 }
      );
      if (!data?.authenticated || !data?.user?.email) {
        throw new Error(data?.error || 'Falha no login.');
      }
      const nextUser: HubUser = {
        id: String(data.user.id),
        email: String(data.user.email),
        name: String(data.user.name || data.user.email),
      };
      const nextToken = typeof data.token === 'string' ? data.token : null;
      setUser(nextUser);
      setToken(nextToken);
      writeStoredSession({ user: nextUser, token: nextToken });
      return nextUser;
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const apiError = err.response?.data?.error;
        if (typeof apiError === 'string' && apiError.trim()) {
          throw new Error(apiError);
        }
        if (err.response?.status === 401) {
          throw new Error('Usuário ou senha inválidos');
        }
        if (err.code === 'ECONNABORTED') {
          throw new Error('Tempo esgotado ao conectar no Hub. Confira se o gateway está no ar.');
        }
        if (!err.response) {
          throw new Error('Não foi possível alcançar a API do Hub (/hub-api).');
        }
      }
      throw err instanceof Error ? err : new Error('Falha no login.');
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    writeStoredSession(null);
  }, []);

  const adoptEmail = useCallback((email: string) => {
    const normalized = email.trim().toLowerCase();
    if (!normalized.includes('@')) return;
    setUser((prev) => {
      if (prev?.email === normalized) return prev;
      const next: HubUser = {
        id: prev?.id || '',
        email: normalized,
        name: prev?.name || normalized.split('@')[0] || 'LeActioner',
      };
      writeStoredSession({ user: next, token: null });
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({ user, token, hydrated, login, logout, adoptEmail }),
    [user, token, hydrated, login, logout, adoptEmail]
  );

  return <HubSessionContext.Provider value={value}>{children}</HubSessionContext.Provider>;
}

export function useHubSession() {
  const ctx = useContext(HubSessionContext);
  if (!ctx) {
    throw new Error('useHubSession must be used within a HubSessionProvider');
  }
  return ctx;
}
