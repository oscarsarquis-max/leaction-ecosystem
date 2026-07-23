'use client';

import Link from 'next/link';
import {
  Building2,
  CreditCard,
  FileText,
  LogIn,
  LogOut,
  Radio,
  ShoppingCart,
  UserRound,
} from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import { useCart } from '@/context/CartContext';
import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { REQUIRE_LOGIN_EVENT, useAuthGate } from '@/lib/require-hub-login';

export function ActionCenter() {
  const router = useRouter();
  const { user, hydrated, login, logout } = useHubSession();
  const { isAuthenticated, requireLogin } = useAuthGate();
  const { cartItems } = useCart();
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
        router.push(next.includes('email=') ? next : `${next}${next.includes('?') ? '&' : '?'}email=${encodeURIComponent(nextUser.email)}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha no login');
    } finally {
      setBusy(false);
    }
  }

  const initials = (user?.name || user?.email || '?')
    .split(/\s+|@/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() || '')
    .join('');

  const companyGuess =
    user?.email?.includes('@') ? user.email.split('@')[1] : 'Conta ActionHub';

  const dashboardHref = user?.email
    ? `/dashboard?email=${encodeURIComponent(user.email)}`
    : '/dashboard';
  const cartHref = user?.email
    ? `/dashboard?email=${encodeURIComponent(user.email)}&view=cart`
    : '/dashboard?view=cart';

  return (
    <aside className="flex h-full flex-col gap-4 overflow-y-auto">
      {/* Perfil / Login */}
      <section
        id="actionhub-login"
        className="scroll-mt-4 rounded-2xl border border-stone-200 bg-white p-4 shadow-sm"
      >
        {!hydrated ? (
          <div className="h-16 animate-pulse rounded-xl bg-stone-100" />
        ) : user ? (
          <div className="flex items-start gap-3">
            <div className="flex size-11 shrink-0 items-center justify-center rounded-full bg-orange-50 text-sm font-bold text-orange-800">
              {initials || <UserRound className="size-5" />}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-stone-900">
                {user.name || 'LeActioner'}
              </p>
              <p className="truncate text-xs text-stone-500">{user.email}</p>
              <p className="mt-1 inline-flex items-center gap-1 text-[11px] font-medium text-stone-400">
                <Building2 className="size-3" aria-hidden />
                {companyGuess}
              </p>
            </div>
            <button
              type="button"
              onClick={() => logout()}
              className="rounded-lg p-1.5 text-stone-400 transition hover:bg-stone-100 hover:text-stone-700"
              title="Sair"
              aria-label="Sair"
            >
              <LogOut className="size-4" />
            </button>
          </div>
        ) : (
          <form onSubmit={onLogin} className="space-y-2">
            <p className="text-sm font-semibold text-stone-900">Entrar no ActionHub</p>
            {loginHint ? (
              <p className="rounded-lg bg-orange-50 px-2.5 py-2 text-xs font-medium text-orange-800">
                {loginHint}
              </p>
            ) : null}
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="E-mail"
              className="w-full rounded-lg border border-stone-200 px-3 py-2 text-sm outline-none focus:border-orange-300 focus:ring-2 focus:ring-orange-100"
            />
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Senha"
              className="w-full rounded-lg border border-stone-200 px-3 py-2 text-sm outline-none focus:border-orange-300 focus:ring-2 focus:ring-orange-100"
            />
            {error ? <p className="text-xs text-red-600">{error}</p> : null}
            <button
              type="submit"
              disabled={busy}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-orange-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-orange-600 disabled:opacity-60"
            >
              <LogIn className="size-4" aria-hidden />
              {busy ? 'Entrando…' : 'Entrar'}
            </button>
          </form>
        )}
      </section>

      {/* Action-Sponge Live Status */}
      <section className="rounded-2xl bg-stone-900 p-5 text-white shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wider text-stone-400">
            Action-Sponge
          </p>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-2 py-0.5 text-[10px] font-semibold text-orange-300">
            <span className="relative flex size-1.5">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex size-1.5 rounded-full bg-emerald-400" />
            </span>
            Live Status
          </span>
        </div>
        <div className="mb-1 flex items-center gap-2 text-orange-300">
          <Radio className="size-4" aria-hidden />
          <span className="text-sm font-medium">Tracking CRM</span>
        </div>
        <dl className="mt-4 space-y-3">
          <div className="flex items-baseline justify-between">
            <dt className="text-sm text-stone-400">Visitas hoje</dt>
            <dd className="text-2xl font-bold tabular-nums">142</dd>
          </div>
          <div className="flex items-baseline justify-between">
            <dt className="text-sm text-stone-400">Drop-off</dt>
            <dd className="text-2xl font-bold tabular-nums text-orange-400">12%</dd>
          </div>
          <div className="flex items-baseline justify-between border-t border-white/10 pt-3">
            <dt className="text-sm text-stone-400">Carrinho</dt>
            <dd className="text-lg font-semibold tabular-nums">{cartItems.length}</dd>
          </div>
        </dl>
        <button
          type="button"
          onClick={() => {
            if (!requireLogin('/dashboard/crm/tracking', 'Faça login para abrir o Analytics.')) {
              return;
            }
            router.push('/dashboard/crm/tracking');
          }}
          className="mt-4 inline-flex w-full items-center justify-center rounded-xl bg-orange-500 px-3 py-2 text-xs font-semibold text-white transition hover:bg-orange-600"
        >
          Abrir Analytics
        </button>
      </section>

      {/* Acessos rápidos */}
      <section className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-stone-400">
          Acessos rápidos
        </p>
        <ul className="space-y-1">
          <li>
            <button
              type="button"
              onClick={() => {
                if (!requireLogin(dashboardHref, 'Faça login para acessar o Action-Pay.')) {
                  return;
                }
                router.push(dashboardHref);
              }}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium text-stone-700 transition hover:bg-orange-50 hover:text-orange-900"
            >
              <CreditCard className="size-4 text-orange-600" aria-hidden />
              Action-Pay (Pagamentos)
            </button>
          </li>
          <li>
            <Link
              href="/dashboard"
              className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-stone-700 transition hover:bg-orange-50 hover:text-orange-900"
              onClick={(e) => {
                if (!isAuthenticated) {
                  e.preventDefault();
                  requireLogin('/dashboard', 'Faça login para ver relatórios.');
                }
              }}
            >
              <FileText className="size-4 text-orange-600" aria-hidden />
              Meus Relatórios
            </Link>
          </li>
          <li>
            <button
              type="button"
              onClick={() => {
                if (!requireLogin(dashboardHref, 'Faça login para ver contratos.')) return;
                router.push(dashboardHref);
              }}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium text-stone-700 transition hover:bg-orange-50 hover:text-orange-900"
            >
              <Building2 className="size-4 text-orange-600" aria-hidden />
              Meus Contratos
            </button>
          </li>
          <li>
            <button
              type="button"
              onClick={() => {
                if (
                  !requireLogin(cartHref, 'Faça login para acessar o carrinho do Marketplace.')
                ) {
                  return;
                }
                router.push(cartHref);
              }}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium text-stone-700 transition hover:bg-orange-50 hover:text-orange-900"
            >
              <ShoppingCart className="size-4 text-orange-600" aria-hidden />
              Carrinho
              {cartItems.length > 0 ? (
                <span className="ml-auto rounded-full bg-orange-50 px-2 py-0.5 text-[11px] font-bold text-orange-700">
                  {cartItems.length}
                </span>
              ) : null}
            </button>
          </li>
        </ul>
      </section>
    </aside>
  );
}
