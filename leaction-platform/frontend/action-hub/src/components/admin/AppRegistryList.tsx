'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { Gift, Loader2, Package, Pencil, RefreshCw } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import { fetchAdminApps, type AdminApp } from '@/lib/admin-api';
import { InjectCreditsModal } from '@/components/admin/InjectCreditsModal';
import { AppEditModal } from '@/components/admin/AppEditModal';

export function AppRegistryList() {
  const { token } = useHubSession();
  const [apps, setApps] = useState<AdminApp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [injectOpen, setInjectOpen] = useState(false);
  const [editApp, setEditApp] = useState<AdminApp | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const rows = await fetchAdminApps(token);
      setApps(rows);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error ||
        (err as Error)?.message ||
        'Falha ao carregar aplicações';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-stone-900 md:text-2xl">
            Aplicações Integradas
          </h1>
          <p className="mt-1 text-sm text-stone-500">
            Registro de apps satélites (`app_registry`) conectadas ao Action Hub.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setSuccess(null);
              setInjectOpen(true);
            }}
            className="inline-flex items-center gap-2 rounded-xl border border-orange-200 bg-orange-50 px-3 py-2 text-sm font-semibold text-orange-900 transition hover:bg-orange-100"
          >
            <Gift className="size-4" aria-hidden />
            Injetar Créditos (Cortesia)
          </button>
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-50 disabled:opacity-60"
          >
            {loading ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <RefreshCw className="size-4" aria-hidden />
            )}
            Atualizar
          </button>
        </div>
      </div>

      {success ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          {success}
        </div>
      ) : null}

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      ) : null}

      <div className="overflow-x-auto rounded-xl border border-stone-200">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-stone-50 text-xs font-semibold uppercase tracking-wide text-stone-500">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Nome</th>
              <th className="px-4 py-3">Webhook</th>
              <th className="px-4 py-3">Secret</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {loading && apps.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-stone-500">
                  <Loader2 className="mx-auto size-5 animate-spin" aria-hidden />
                </td>
              </tr>
            ) : null}
            {!loading && apps.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-stone-500">
                  Nenhuma aplicação cadastrada.
                </td>
              </tr>
            ) : null}
            {apps.map((app) => (
              <tr key={app.app_id} className="bg-white hover:bg-orange-50/40">
                <td className="px-4 py-3 font-mono text-xs text-stone-700">
                  {app.app_id}
                </td>
                <td className="px-4 py-3 font-semibold text-stone-900">{app.name}</td>
                <td className="max-w-[16rem] truncate px-4 py-3 text-stone-600">
                  {app.webhook_url || (
                    <span className="text-stone-400">não configurado</span>
                  )}
                </td>
                <td className="px-4 py-3 text-xs text-stone-500">
                  {app.has_secret ? app.secret_hint || '••••' : '—'}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      app.active
                        ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200'
                        : 'bg-stone-100 text-stone-600 ring-1 ring-stone-200'
                    }`}
                  >
                    {app.active ? 'Ativo' : 'Inativo'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="inline-flex flex-wrap items-center justify-end gap-1.5">
                    <button
                      type="button"
                      onClick={() => {
                        setSuccess(null);
                        setEditApp(app);
                      }}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-xs font-semibold text-stone-700 transition hover:bg-stone-50"
                    >
                      <Pencil className="size-3.5" aria-hidden />
                      Integrar
                    </button>
                    <Link
                      href={`/dashboard/admin/plans?app_id=${encodeURIComponent(app.app_id)}`}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-orange-500 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-orange-600"
                    >
                      <Package className="size-3.5" aria-hidden />
                      Planos
                    </Link>
                    <Link
                      href={`/dashboard/admin/payments?app_id=${encodeURIComponent(app.app_id)}`}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-orange-200 bg-orange-50 px-3 py-1.5 text-xs font-semibold text-orange-900 transition hover:bg-orange-100"
                    >
                      Pagamentos
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <InjectCreditsModal
        open={injectOpen}
        token={token}
        apps={apps}
        onClose={() => setInjectOpen(false)}
        onSuccess={(message) => {
          setSuccess(message);
          void load();
        }}
      />

      <AppEditModal
        open={Boolean(editApp)}
        token={token}
        app={editApp}
        onClose={() => setEditApp(null)}
        onSuccess={(message) => {
          setSuccess(message);
          void load();
        }}
      />
    </div>
  );
}
