'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Loader2, Lock } from 'lucide-react';
import { useAuthGate } from '@/lib/require-hub-login';

type Alerta = {
  chave: string;
  severidade: 'alta' | 'media' | string;
  explicacao?: string;
};

type ContaPosVenda = {
  instituicao_id: string;
  nome: string;
  contratou_em: string | null;
  dias_de_contrato: number | null;
  etapa_atual: number;
  etapa_atual_rotulo?: string;
  professores?: { convidados: number; aceitos: number; usando: number };
  licencas?: { em_uso: number; total: number };
  alertas?: Alerta[];
  pontuacao?: number;
};

type ListaResponse = {
  ok?: boolean;
  error?: string;
  contas?: ContaPosVenda[];
  meta?: { elapsed_ms?: number };
};

const ALERTA_OPTS = [
  { id: '', label: 'Todos' },
  { id: 'pagou_nao_logou', label: 'Pagou e não logou' },
  { id: 'logou_nao_montou', label: 'Logou e não montou' },
  { id: 'convites_sem_aceite', label: 'Convites sem aceite' },
  { id: 'aceitou_nao_usou', label: 'Aceitou e não usou' },
  { id: 'parou_de_usar', label: 'Parou de usar' },
  { id: 'licenca_ociosa', label: 'Licença ociosa' },
];

function chipClass(sev: string) {
  return sev === 'alta'
    ? 'bg-red-50 text-red-800 ring-red-200'
    : 'bg-amber-50 text-amber-900 ring-amber-200';
}

function PosVendaInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { hydrated, isAuthenticated, requireLogin } = useAuthGate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState<ListaResponse | null>(null);
  const alerta = (searchParams.get('alerta') || '').trim();

  useEffect(() => {
    if (!hydrated) return;
    if (!isAuthenticated) {
      requireLogin('/dashboard/crm/pos-venda', 'Faça login para acessar o pós-venda do Sponge.');
    }
  }, [hydrated, isAuthenticated, requireLogin]);

  const load = useCallback(async () => {
    const qs = new URLSearchParams();
    if (alerta) qs.set('alerta', alerta);
    const res = await fetch(`/api/crm/pos-venda${qs.toString() ? `?${qs}` : ''}`, {
      cache: 'no-store',
    });
    const json = (await res.json()) as ListaResponse;
    if (!res.ok || json.ok === false) {
      throw new Error(json.error || `HTTP ${res.status}`);
    }
    return json;
  }, [alerta]);

  useEffect(() => {
    if (!hydrated || !isAuthenticated) return;
    let cancelled = false;
    setLoading(true);
    setError('');
    load()
      .then((json) => {
        if (!cancelled) setData(json);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Falha ao carregar');
          setData(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [hydrated, isAuthenticated, load]);

  const contas = data?.contas || [];
  const atencao = useMemo(
    () => contas.filter((c) => (c.alertas || []).some((a) => a.severidade === 'alta')),
    [contas]
  );

  if (!hydrated) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center bg-stone-50 text-stone-500">
        <Loader2 className="size-5 animate-spin" aria-hidden />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 bg-stone-50 px-4 text-center">
        <Lock className="size-8 text-emerald-600" aria-hidden />
        <p className="text-sm text-stone-500">Login necessário.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <div className="mx-auto max-w-7xl px-4 py-8 md:px-6 md:py-10">
        <Link
          href="/dashboard/crm/uso"
          className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-emerald-800"
        >
          <ArrowLeft className="size-4" aria-hidden />
          Uso
        </Link>
        <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-stone-900">Pós-venda</h1>
            <p className="mt-1 text-sm text-stone-500">
              Onboarding por conta e contas que precisam de atenção
            </p>
          </div>
          <label className="text-sm">
            <span className="mr-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Alerta
            </span>
            <select
              value={alerta}
              onChange={(e) => {
                const v = e.target.value;
                router.replace(v ? `/dashboard/crm/pos-venda?alerta=${encodeURIComponent(v)}` : '/dashboard/crm/pos-venda');
              }}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            >
              {ALERTA_OPTS.map((o) => (
                <option key={o.id || 'all'} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        </header>

        {atencao.length ? (
          <section className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4">
            <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-red-800">
              Precisam de atenção
            </h2>
            <ul className="space-y-1 text-sm">
              {atencao.map((c) => (
                <li key={c.instituicao_id}>
                  <button
                    type="button"
                    className="font-semibold text-red-900 hover:underline"
                    onClick={() =>
                      router.push(`/dashboard/crm/contas/${c.instituicao_id}/pos-venda`)
                    }
                  >
                    {c.nome}
                  </button>
                  <span className="ml-2 text-red-700">
                    {(c.alertas || [])
                      .filter((a) => a.severidade === 'alta')
                      .map((a) => a.chave)
                      .join(', ')}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {loading ? (
          <div className="flex justify-center py-16 text-slate-400">
            <Loader2 className="size-6 animate-spin" aria-hidden />
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {error}
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Conta</th>
                  <th className="px-4 py-3">Dias</th>
                  <th className="px-4 py-3">Etapa</th>
                  <th className="px-4 py-3">Professores</th>
                  <th className="px-4 py-3">Licenças</th>
                  <th className="px-4 py-3">Alertas</th>
                </tr>
              </thead>
              <tbody>
                {contas.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                      nenhuma conta no recorte
                    </td>
                  </tr>
                ) : (
                  contas.map((c) => (
                    <tr
                      key={c.instituicao_id}
                      className="cursor-pointer border-t border-slate-100 hover:bg-slate-50"
                      onClick={() =>
                        router.push(`/dashboard/crm/contas/${c.instituicao_id}/pos-venda`)
                      }
                    >
                      <td className="px-4 py-3 font-medium text-stone-900">{c.nome}</td>
                      <td className="px-4 py-3 tabular-nums">{c.dias_de_contrato ?? '—'}</td>
                      <td className="px-4 py-3">
                        {c.etapa_atual}/9
                        <span className="ml-1 text-xs text-slate-500">
                          {c.etapa_atual_rotulo}
                        </span>
                      </td>
                      <td className="px-4 py-3 tabular-nums">
                        {c.professores?.convidados ?? 0}/{c.professores?.aceitos ?? 0}/
                        {c.professores?.usando ?? 0}
                      </td>
                      <td className="px-4 py-3 tabular-nums">
                        {c.licencas?.em_uso ?? 0}/{c.licencas?.total ?? 0}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {(c.alertas || []).map((a) => (
                            <span
                              key={a.chave}
                              className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${chipClass(a.severidade)}`}
                            >
                              {a.chave}
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default function CrmPosVendaPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[50vh] items-center justify-center bg-stone-50 text-stone-500">
          <Loader2 className="size-5 animate-spin" aria-hidden />
        </div>
      }
    >
      <PosVendaInner />
    </Suspense>
  );
}
