'use client';

import { useState } from 'react';
import axios from 'axios';
import { Loader2, Lock, LogIn } from 'lucide-react';

type CurationLoginProps = {
  onSuccess: () => void;
};

export function CurationLogin({ onSuccess }: CurationLoginProps) {
  const [user, setUser] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const { data } = await axios.post(
        '/api/marketplace/curation-auth/login',
        { user, password },
        { timeout: 10000 }
      );
      if (!data?.authenticated) {
        throw new Error(data?.error || 'Falha no login.');
      }
      onSuccess();
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.data?.error) {
        setError(String(err.response.data.error));
      } else {
        setError(err instanceof Error ? err.message : 'Erro ao entrar.');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center justify-center px-2 py-8">
      <div className="w-full max-w-md rounded-2xl border border-stone-200 bg-white p-8 shadow-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-orange-50">
            <Lock className="size-7 text-orange-500" aria-hidden />
          </div>
          <h1 className="text-2xl font-extrabold text-red-950">Curadoria Marketplace</h1>
          <p className="mt-2 text-sm text-red-950/70">Área administrativa — faça login para continuar.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="curation-user" className="mb-1 block text-sm font-semibold text-red-950">
              Usuário
            </label>
            <input
              id="curation-user"
              type="text"
              autoComplete="username"
              value={user}
              onChange={(e) => setUser(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm text-red-950 focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-200"
              required
            />
          </div>
          <div>
            <label htmlFor="curation-password" className="mb-1 block text-sm font-semibold text-red-950">
              Senha
            </label>
            <input
              id="curation-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm text-red-950 focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-200"
              required
            />
          </div>

          {error ? (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-3 text-sm font-bold text-white hover:bg-red-700 disabled:opacity-60"
          >
            {loading ? <Loader2 className="size-4 animate-spin" /> : <LogIn className="size-4" />}
            Entrar
          </button>
        </form>
      </div>
    </div>
  );
}
