'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Gift, Loader2, Pencil, Plus, RefreshCw } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import {
  createAdminPlan,
  fetchAdminApps,
  fetchAdminPlans,
  formatBrl,
  planTypeLabel,
  updateAdminPlan,
  type AdminApp,
  type CatalogPlan,
  type PlanUpsertBody,
} from '@/lib/admin-api';
import { InjectCreditsModal } from '@/components/admin/InjectCreditsModal';
import { PlanFormModal } from '@/components/admin/PlanFormModal';

type Props = {
  initialAppId?: string;
};

export function PlanBuilder({ initialAppId = '' }: Props) {
  const { token } = useHubSession();
  const router = useRouter();
  const [apps, setApps] = useState<AdminApp[]>([]);
  const [appId, setAppId] = useState(initialAppId);
  const [plans, setPlans] = useState<CatalogPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<CatalogPlan | null>(null);
  const [injectOpen, setInjectOpen] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    setAppId(initialAppId);
  }, [initialAppId]);

  const loadApps = useCallback(async () => {
    if (!token) return;
    try {
      const rows = await fetchAdminApps(token);
      setApps(rows);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error ||
        (err as Error)?.message ||
        'Falha ao carregar apps';
      setError(msg);
    }
  }, [token]);

  const loadPlans = useCallback(async () => {
    if (!token || !appId) {
      setPlans([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const rows = await fetchAdminPlans(token, appId);
      setPlans(rows);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error ||
        (err as Error)?.message ||
        'Falha ao carregar planos';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [token, appId]);

  useEffect(() => {
    void loadApps();
  }, [loadApps]);

  useEffect(() => {
    if (!appId && apps[0]?.app_id) {
      setAppId(apps[0].app_id);
    }
  }, [apps, appId]);

  useEffect(() => {
    void loadPlans();
  }, [loadPlans]);
  const selectedAppName = useMemo(
    () => apps.find((a) => a.app_id === appId)?.name || appId,
    [apps, appId]
  );

  function selectApp(next: string) {
    setAppId(next);
    const params = new URLSearchParams();
    if (next) params.set('app_id', next);
    router.replace(
      `/dashboard/admin/plans${params.toString() ? `?${params}` : ''}`
    );
  }

  async function handleSave(body: PlanUpsertBody & { app_id: string }) {
    if (!token) throw new Error('Token ausente');
    if (editing?.id) {
      await updateAdminPlan(token, editing.id, body);
    } else {
      await createAdminPlan(token, body);
    }
    await loadPlans();
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-stone-900 md:text-2xl">
            Construtor de Planos
          </h1>
          <p className="mt-1 text-sm text-stone-500">
            Catálogo da vitrine por aplicação satélite
            {selectedAppName ? (
              <>
                {' '}
                · <span className="font-semibold text-stone-700">{selectedAppName}</span>
              </>
            ) : null}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={!appId}
            onClick={() => {
              setSuccess(null);
              setInjectOpen(true);
            }}
            className="inline-flex items-center gap-2 rounded-xl border border-orange-200 bg-orange-50 px-3 py-2 text-sm font-semibold text-orange-900 transition hover:bg-orange-100 disabled:opacity-60"
          >
            <Gift className="size-4" aria-hidden />
            Injetar Créditos (Cortesia)
          </button>
          <button
            type="button"
            onClick={() => void loadPlans()}
            disabled={loading || !appId}
            className="inline-flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-50 disabled:opacity-60"
          >
            {loading ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <RefreshCw className="size-4" aria-hidden />
            )}
            Atualizar
          </button>
          <button
            type="button"
            disabled={!appId}
            onClick={() => {
              setEditing(null);
              setModalOpen(true);
            }}
            className="inline-flex items-center gap-2 rounded-xl bg-orange-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-orange-600 disabled:opacity-60"
          >
            <Plus className="size-4" aria-hidden />
            Novo plano
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-stone-200 bg-stone-50/80 px-3 py-3">
        <label className="flex min-w-[14rem] flex-1 flex-col gap-1">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
            Aplicação
          </span>
          <select
            value={appId}
            onChange={(e) => selectApp(e.target.value)}
            className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm font-semibold text-stone-800 outline-none ring-orange-200 focus:ring-2"
          >
            {apps.length === 0 ? (
              <option value="">Carregando apps…</option>
            ) : (
              apps.map((app) => (
                <option key={app.app_id} value={app.app_id}>
                  {app.name} ({app.app_id})
                </option>
              ))
            )}
          </select>
        </label>
        <Link
          href="/dashboard/admin/apps"
          className="self-end text-sm font-medium text-orange-700 hover:underline"
        >
          Ver aplicações
        </Link>
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

      {loading && plans.length === 0 ? (
        <div className="flex items-center justify-center py-16 text-stone-500">
          <Loader2 className="size-6 animate-spin" aria-hidden />
        </div>
      ) : null}

      {!loading && plans.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-stone-200 px-6 py-12 text-center">
          <p className="text-sm font-semibold text-stone-700">
            Nenhum plano para esta aplicação
          </p>
          <p className="mt-1 text-sm text-stone-500">
            Crie o primeiro pacote ou assinatura da vitrine.
          </p>
          <button
            type="button"
            disabled={!appId}
            onClick={() => {
              setEditing(null);
              setModalOpen(true);
            }}
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-600"
          >
            <Plus className="size-4" aria-hidden />
            Criar plano
          </button>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {plans.map((plan) => {
          const entitlements =
            plan.meta_json &&
            typeof plan.meta_json.entitlements === 'object' &&
            plan.meta_json.entitlements
              ? (plan.meta_json.entitlements as Record<string, unknown>)
              : plan.meta_json || {};
          return (
            <article
              key={plan.id}
              className="flex flex-col rounded-2xl border border-stone-200 bg-white p-4 shadow-sm"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <h2 className="truncate text-base font-bold text-stone-900">
                    {plan.name}
                  </h2>
                  <p className="mt-0.5 font-mono text-xs text-stone-500">{plan.sku}</p>
                </div>
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                    plan.active
                      ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200'
                      : 'bg-stone-100 text-stone-600 ring-1 ring-stone-200'
                  }`}
                >
                  {plan.active ? 'Ativo' : 'Inativo'}
                </span>
              </div>
              <p className="mt-3 text-2xl font-bold tracking-tight text-orange-900">
                {formatBrl(plan.price, plan.currency)}
              </p>
              <p className="mt-1 text-xs font-medium text-stone-500">
                {planTypeLabel(plan.type)}
              </p>
              {Object.keys(entitlements).length > 0 ? (
                <ul className="mt-3 space-y-1 border-t border-stone-100 pt-3 text-xs text-stone-600">
                  {Object.entries(entitlements)
                    .slice(0, 6)
                    .map(([k, v]) => (
                      <li key={k} className="flex justify-between gap-2">
                        <span className="font-mono text-stone-500">{k}</span>
                        <span className="font-semibold text-stone-800">
                          {String(v)}
                        </span>
                      </li>
                    ))}
                </ul>
              ) : null}
              <button
                type="button"
                onClick={() => {
                  setEditing(plan);
                  setModalOpen(true);
                }}
                className="mt-4 inline-flex items-center justify-center gap-1.5 rounded-xl border border-stone-200 px-3 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-50"
              >
                <Pencil className="size-3.5" aria-hidden />
                Editar
              </button>
            </article>
          );
        })}
      </div>

      {appId ? (
        <PlanFormModal
          open={modalOpen}
          appId={appId}
          plan={editing}
          onClose={() => {
            setModalOpen(false);
            setEditing(null);
          }}
          onSave={handleSave}
        />
      ) : null}

      <InjectCreditsModal
        open={injectOpen}
        token={token}
        apps={apps}
        lockedAppId={appId}
        onClose={() => setInjectOpen(false)}
        onSuccess={(message) => setSuccess(message)}
      />
    </div>
  );
}
