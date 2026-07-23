'use client';

import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, TrendingDown, TrendingUp } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import { REQUIRE_LOGIN_EVENT } from '@/lib/require-hub-login';
import {
  MARKET_TICKERS,
  SECTOR_HEADLINES,
} from '@/components/public-portal/mock-data';

/** Coluna direita — login + radar executivo. */
export function PortalAccessColumn() {
  const router = useRouter();
  const { login, hydrated } = useHubSession();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [loginHint, setLoginHint] = useState('');

  useEffect(() => {
    function onRequireLogin(event: Event) {
      const detail = (event as CustomEvent<{ reason?: string }>).detail;
      setLoginHint(detail?.reason || 'Faça login para continuar.');
      document.getElementById('actionhub-login')?.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
    window.addEventListener(REQUIRE_LOGIN_EVENT, onRequireLogin);
    return () => window.removeEventListener(REQUIRE_LOGIN_EVENT, onRequireLogin);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const reason = params.get('login_reason');
    if (reason) setLoginHint(reason);
  }, []);

  async function onLogin(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const nextUser = await login(email.trim(), password);
      setPassword('');
      setLoginHint('');
      const params = new URLSearchParams(window.location.search);
      const next = params.get('next');
      if (next && next.startsWith('/')) {
        router.push(
          next.includes('email=')
            ? next
            : `${next}${next.includes('?') ? '&' : '?'}email=${encodeURIComponent(nextUser.email)}`
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha no login');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col gap-4">
      {/* Login — id estável para requireLogin / CTA do hero */}
      <section
        id="actionhub-login"
        className="scroll-mt-4 rounded-2xl border border-stone-200 border-t-4 border-t-orange-500 bg-white p-5 shadow-sm"
      >
        <h2 className="text-base font-bold text-stone-900">Acesso à Plataforma</h2>
        <p className="mt-1 text-xs text-stone-500">Portal executivo ActionHub</p>

        {!hydrated ? (
          <div className="mt-4 h-28 animate-pulse rounded-xl bg-stone-100" />
        ) : (
          <form onSubmit={onLogin} className="mt-4 space-y-3">
            {loginHint ? (
              <p className="rounded-lg bg-orange-50 px-3 py-2 text-xs font-medium text-orange-800">
                {loginHint}
              </p>
            ) : null}
            <label className="block">
              <span className="mb-1 block text-xs font-semibold text-stone-500">E-mail</span>
              <input
                type="email"
                required
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="voce@empresa.com"
                className="w-full rounded-xl border border-stone-200 bg-white px-3 py-2.5 text-sm text-stone-900 outline-none placeholder:text-stone-400 focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-semibold text-stone-500">Senha</span>
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border border-stone-200 bg-white px-3 py-2.5 text-sm text-stone-900 outline-none placeholder:text-stone-400 focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
              />
            </label>
            {error ? (
              <p className="text-xs font-medium text-red-600" role="alert">
                {error}
              </p>
            ) : null}
            <button
              type="submit"
              disabled={busy}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-orange-500 py-2.5 text-sm font-bold text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : null}
              Entrar
            </button>
            <a
              href="mailto:contato@actionhub.com.br?subject=Solicitar%20acesso%20ActionHub"
              className="block text-center text-xs font-medium text-stone-500 transition hover:text-orange-600"
            >
              Ainda não faz parte? Solicite acesso.
            </a>
          </form>
        )}
      </section>

      {/* Radar B2B */}
      <section className="rounded-2xl bg-stone-900 p-5 text-stone-100 shadow-sm">
        <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-stone-400">
          Radar B2B
        </p>
        <p className="mt-1 text-sm font-semibold text-white">Contexto de mercado</p>
        <ul className="mt-4 space-y-3">
          {MARKET_TICKERS.map((tick) => (
            <li key={tick.id} className="flex items-center justify-between gap-2 text-sm">
              <span className="font-medium text-stone-300">{tick.label}</span>
              <span className="inline-flex items-center gap-1.5 font-semibold text-white">
                {tick.value}
                {tick.trend === 'up' ? (
                  <TrendingUp className="size-3.5 text-emerald-400" aria-label="alta" />
                ) : (
                  <TrendingDown className="size-3.5 text-rose-400" aria-label="baixa" />
                )}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {/* Radar setorial */}
      <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-bold text-stone-900">Radar de Inovação</h2>
        <ul className="mt-3 space-y-3">
          {SECTOR_HEADLINES.map((item) => (
            <li
              key={item.id}
              className="border-l-2 border-orange-500 pl-3 text-sm leading-snug text-stone-500"
            >
              {item.title}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
