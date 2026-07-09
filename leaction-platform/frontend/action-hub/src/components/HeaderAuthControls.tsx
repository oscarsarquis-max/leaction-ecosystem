'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Loader2, LogIn, LogOut, ShoppingCart } from 'lucide-react';
import axios from 'axios';
import { useCart } from '@/context/CartContext';
import { useHubSession } from '@/context/HubSessionContext';
import { getHubApiBase } from '@/lib/hub-api';

function cartItemsToSkus(items: { id?: string | number; sku?: string }[]): string[] {
  return items
    .map((item) => {
      const sku = item.sku != null ? String(item.sku).trim() : '';
      if (sku) return sku;
      return String(item.id ?? '').trim();
    })
    .filter(Boolean);
}

function CartIconLink({
  href,
  isAnonymous,
  variant,
}: {
  href: string;
  isAnonymous: boolean;
  variant: 'light' | 'dark';
}) {
  const { cartItems, cartHydrated } = useCart();
  const count = cartItems.length;
  const prevCountRef = useRef<number | null>(null);
  const [pulseCart, setPulseCart] = useState(false);
  const isLight = variant === 'light';

  useEffect(() => {
    if (!cartHydrated) return;
    const prev = prevCountRef.current;
    if (prev === null) {
      prevCountRef.current = count;
      return;
    }
    if (
      isAnonymous &&
      prev === 0 &&
      count === 1 &&
      typeof window !== 'undefined' &&
      !window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      setPulseCart(true);
    }
    prevCountRef.current = count;
  }, [count, isAnonymous, cartHydrated]);

  useEffect(() => {
    if (!pulseCart) return;
    const t = window.setTimeout(() => setPulseCart(false), 2000);
    return () => window.clearTimeout(t);
  }, [pulseCart]);

  return (
    <Link
      href={href}
      className={
        isLight
          ? 'relative inline-flex items-center justify-center rounded-lg p-2 text-slate-600 transition hover:bg-slate-100 hover:text-red-900'
          : 'relative inline-flex items-center justify-center rounded-lg p-2 text-orange-200 transition hover:bg-white/10 hover:text-white'
      }
      aria-label={count > 0 ? `Carrinho com ${count} item(ns)` : 'Carrinho'}
    >
      <span className={`inline-flex ${pulseCart ? 'animate-cart-pulse' : ''}`}>
        <ShoppingCart className="size-5 md:size-6" />
      </span>
      {count > 0 ? (
        <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-orange-500 px-1 text-[10px] font-bold leading-none text-white">
          {count > 99 ? '99+' : count}
        </span>
      ) : null}
    </Link>
  );
}

type HeaderAuthControlsProps = {
  variant?: 'light' | 'dark';
};

/**
 * Login compacto (usuário + senha + ícone) / Sair + carrinho.
 * Browse anônimo OK; histórico/checkout exigem sessão.
 */
export function HeaderAuthControls({ variant = 'dark' }: HeaderAuthControlsProps) {
  const router = useRouter();
  const { user, hydrated, login, logout } = useHubSession();
  const { cartItems, setCartItems } = useCart();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const isLight = variant === 'light';

  const cartHref = user?.email
    ? `/dashboard?email=${encodeURIComponent(user.email)}&view=cart`
    : '/dashboard?view=cart';
  const historyHref = user?.email
    ? `/dashboard?email=${encodeURIComponent(user.email)}`
    : '/dashboard';

  const handleLogin = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    const emailTyped = email.trim();
    if (!emailTyped.includes('@')) {
      setError('E-mail inválido');
      return;
    }
    if (password.length < 4) {
      setError('Senha curta');
      return;
    }

    setBusy(true);
    try {
      const nextUser = await login(emailTyped, password);
      const skus = cartItemsToSkus(cartItems);
      if (skus.length > 0) {
        try {
          await axios.post(`${getHubApiBase()}/sync-cart`, {
            email: nextUser.email,
            items: skus,
          });
          setCartItems([]);
        } catch {
          /* carrinho local permanece; usuário já autenticado */
        }
      }
      setPassword('');
      router.push(`/dashboard?email=${encodeURIComponent(nextUser.email)}`);
    } catch (err) {
      const msg = axios.isAxiosError(err)
        ? String((err.response?.data as { error?: string } | undefined)?.error || err.message)
        : err instanceof Error
          ? err.message
          : 'Falha no login';
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  const handleLogout = () => {
    logout();
    setEmail('');
    setPassword('');
    setError('');
    router.push('/');
  };

  if (!hydrated) {
    return (
      <div className={`flex items-center gap-2 ${isLight ? 'justify-end' : ''}`}>
        <span
          className={`h-8 w-40 animate-pulse rounded-lg ${isLight ? 'bg-slate-100' : 'bg-white/10'}`}
          aria-hidden
        />
        <CartIconLink href="/dashboard?view=cart" isAnonymous variant={variant} />
      </div>
    );
  }

  if (user) {
    return (
      <div
        className={`flex max-w-[min(100%,28rem)] items-center gap-1.5 sm:gap-2 ${isLight ? 'ml-auto' : ''}`}
      >
        <Link
          href={historyHref}
          className={
            isLight
              ? 'hidden max-w-[10rem] truncate text-xs font-medium text-slate-600 transition hover:text-red-900 sm:inline md:max-w-[14rem] md:text-sm'
              : 'hidden max-w-[10rem] truncate text-xs font-medium text-orange-100/90 transition hover:text-white sm:inline md:max-w-[14rem] md:text-sm'
          }
          title={user.email}
        >
          {user.name || user.email}
        </Link>
        <button
          type="button"
          onClick={handleLogout}
          className={
            isLight
              ? 'inline-flex items-center justify-center rounded-lg p-2 text-slate-600 transition hover:bg-slate-100 hover:text-red-900'
              : 'inline-flex items-center justify-center rounded-lg p-2 text-orange-200 transition hover:bg-white/10 hover:text-white'
          }
          aria-label="Sair"
          title="Sair"
        >
          <LogOut className="size-5" />
        </button>
        <CartIconLink href={cartHref} isAnonymous={false} variant={variant} />
      </div>
    );
  }

  return (
    <div className={`flex max-w-[min(100%,36rem)] flex-col gap-1 ${isLight ? 'ml-auto' : ''}`}>
      <form
        onSubmit={(e) => {
          void handleLogin(e);
        }}
        className="flex items-center gap-1.5"
      >
        <input
          type="email"
          name="hub-email"
          autoComplete="username"
          placeholder="E-mail"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={
            isLight
              ? 'h-9 w-[7.5rem] rounded-lg border border-slate-200 bg-white px-2.5 text-xs text-slate-800 outline-none placeholder:text-slate-400 focus:border-orange-400 focus:ring-2 focus:ring-orange-500/20 sm:w-36 md:w-44 md:text-sm'
              : 'h-9 w-[7.5rem] rounded-lg border border-white/15 bg-white/10 px-2.5 text-xs text-white outline-none placeholder:text-orange-200/50 focus:border-orange-300/60 focus:bg-white/15 sm:w-36 md:w-44 md:text-sm'
          }
          aria-label="E-mail"
        />
        <input
          type="password"
          name="hub-password"
          autoComplete="current-password"
          placeholder="Senha"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={
            isLight
              ? 'h-9 w-[5.5rem] rounded-lg border border-slate-200 bg-white px-2.5 text-xs text-slate-800 outline-none placeholder:text-slate-400 focus:border-orange-400 focus:ring-2 focus:ring-orange-500/20 sm:w-24 md:w-28 md:text-sm'
              : 'h-9 w-[5.5rem] rounded-lg border border-white/15 bg-white/10 px-2.5 text-xs text-white outline-none placeholder:text-orange-200/50 focus:border-orange-300/60 focus:bg-white/15 sm:w-24 md:w-28 md:text-sm'
          }
          aria-label="Senha"
        />
        <button
          type="submit"
          disabled={busy}
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-orange-500 text-white transition hover:bg-orange-400 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label="Entrar"
          title="Entrar"
        >
          {busy ? <Loader2 className="size-4 animate-spin" /> : <LogIn className="size-4" />}
        </button>
        <CartIconLink href={cartHref} isAnonymous variant={variant} />
      </form>
      {error ? (
        <p
          className={`max-w-xs truncate text-[10px] font-medium ${isLight ? 'text-red-600' : 'text-amber-200'}`}
          role="alert"
        >
          {error}
        </p>
      ) : null}
    </div>
  );
}
