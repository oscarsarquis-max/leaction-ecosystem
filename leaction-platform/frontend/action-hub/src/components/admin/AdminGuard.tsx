'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { Lock, ShieldAlert } from 'lucide-react';
import { useAdminGate } from '@/lib/require-admin';

export function AdminGuard({ children }: { children: ReactNode }) {
  const {
    hydrated,
    isAuthenticated,
    isAdmin,
    hasToken,
    canAccessAdmin,
    requireLogin,
  } = useAdminGate();

  if (!hydrated) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center bg-stone-50 text-sm text-stone-500">
        Carregando sessão…
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 bg-stone-50 px-4 text-center">
        <span className="flex size-14 items-center justify-center rounded-2xl bg-orange-50 text-orange-600 ring-1 ring-orange-200">
          <Lock className="size-7" aria-hidden />
        </span>
        <div>
          <h1 className="text-xl font-bold text-stone-900">Área administrativa</h1>
          <p className="mt-1 max-w-md text-sm text-stone-500">
            Faça login com uma conta de administrador para acompanhar pagamentos e o catálogo.
          </p>
        </div>
        <button
          type="button"
          onClick={() =>
            requireLogin(
              '/dashboard/admin/payments',
              'Faça login como administrador para continuar.'
            )
          }
          className="rounded-xl bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-orange-600"
        >
          Ir para login
        </button>
        <Link href="/" className="text-sm font-medium text-stone-500 hover:text-stone-800">
          Voltar à home
        </Link>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 bg-stone-50 px-4 text-center">
        <span className="flex size-14 items-center justify-center rounded-2xl bg-red-50 text-red-600 ring-1 ring-red-200">
          <ShieldAlert className="size-7" aria-hidden />
        </span>
        <div>
          <h1 className="text-xl font-bold text-stone-900">Acesso negado</h1>
          <p className="mt-1 max-w-md text-sm text-stone-500">
            Sua conta está autenticada, mas não possui perfil de Admin no Action Hub.
          </p>
        </div>
        <Link
          href="/"
          className="rounded-xl bg-stone-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-stone-800"
        >
          Voltar ao Action Hub
        </Link>
      </div>
    );
  }

  if (!hasToken || !canAccessAdmin) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 bg-stone-50 px-4 text-center">
        <span className="flex size-14 items-center justify-center rounded-2xl bg-amber-50 text-amber-700 ring-1 ring-amber-200">
          <Lock className="size-7" aria-hidden />
        </span>
        <div>
          <h1 className="text-xl font-bold text-stone-900">Sessão incompleta</h1>
          <p className="mt-1 max-w-md text-sm text-stone-500">
            É necessário entrar com e-mail e senha para obter o token JWT usado nas APIs
            administrativas.
          </p>
        </div>
        <button
          type="button"
          onClick={() =>
            requireLogin(
              '/dashboard/admin/payments',
              'Entre com e-mail e senha de administrador.'
            )
          }
          className="rounded-xl bg-orange-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-orange-600"
        >
          Fazer login completo
        </button>
        <Link href="/" className="text-sm font-medium text-stone-500 hover:text-stone-800">
          Voltar ao Action Hub
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}
