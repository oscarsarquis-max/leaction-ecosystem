'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Building2, Loader2, Lock } from 'lucide-react';
import { useAuthGate } from '@/lib/require-hub-login';

export type ContaListItem = {
  instituicao_id: string;
  nome: string;
  sistemas: string[];
  primeiro_acesso: string | null;
  ultimo_acesso: string | null;
  ultimo_login: string | null;
  sessoes_7d: number;
  sessoes_30d: number;
  usuarios_30d: number;
  tem_contrato: boolean;
  contrato_status: string | null;
  plano: string | null;
};

export function formatSp(iso: string | null | undefined) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
  } catch {
    return '—';
  }
}

export function diasDesde(iso: string | null | undefined) {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return null;
  return Math.floor((Date.now() - t) / 86400000);
}

function CrmContasGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { hydrated, isAuthenticated, requireLogin } = useAuthGate();

  useEffect(() => {
    if (!hydrated) return;
    if (!isAuthenticated) {
      requireLogin('/dashboard/crm/contas', 'Faça login para acessar as contas do Sponge.');
    }
  }, [hydrated, isAuthenticated, requireLogin]);

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
        <span className="flex size-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 ring-1 ring-emerald-200">
          <Lock className="size-7" aria-hidden />
        </span>
        <h1 className="text-xl font-bold text-stone-900">Contas protegidas</h1>
        <p className="max-w-md text-sm text-stone-500">
          A ficha de conta do Action-Sponge só pode ser acessada com login no Action Hub.
        </p>
        <button
          type="button"
          onClick={() =>
            requireLogin('/dashboard/crm/contas', 'Faça login para acessar as contas do Sponge.')
          }
          className="rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-600"
        >
          Ir para login
        </button>
        <button
          type="button"
          onClick={() => router.push('/')}
          className="text-sm font-medium text-stone-500 hover:text-stone-800"
        >
          Voltar à home
        </button>
      </div>
    );
  }

  return <>{children}</>;
}

export default function CrmContasListPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [contas, setContas] = useState<ContaListItem[]>([]);
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);
  const [sistema, setSistema] = useState('');
  const [comContrato, setComContrato] = useState('');
  const [semAcesso, setSemAcesso] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    const qs = new URLSearchParams();
    if (sistema) qs.set('sistema', sistema);
    if (comContrato) qs.set('com_contrato', comContrato);
    if (semAcesso) qs.set('sem_acesso_desde', semAcesso);
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    try {
      const res = await fetch(`/api/crm/contas${suffix}`, { cache: 'no-store' });
      const json = await res.json().catch(() => ({}));
      if (!res.ok || !json?.ok) {
        throw new Error(json?.error || 'Falha ao listar contas');
      }
      setContas(Array.isArray(json.contas) ? json.contas : []);
      setElapsedMs(typeof json?.meta?.elapsed_ms === 'number' ? json.meta.elapsed_ms : null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao listar contas');
      setContas([]);
    } finally {
      setLoading(false);
    }
  }, [sistema, comContrato, semAcesso]);

  useEffect(() => {
    void load();
  }, [load]);

  const sistemasOpts = useMemo(() => {
    const s = new Set<string>();
    for (const c of contas) for (const x of c.sistemas || []) s.add(x);
    return [...s].sort();
  }, [contas]);

  return (
    <CrmContasGate>
      <div className="min-h-screen bg-slate-50 text-slate-800">
        <div className="mx-auto max-w-7xl px-4 py-8 md:px-6 md:py-10">
          <header className="mb-6">
            <Link
              href="/"
              className="mb-3 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-emerald-800"
            >
              <ArrowLeft className="size-4" aria-hidden />
              Voltar ao Action Hub
            </Link>
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-stone-900 md:text-3xl">
                  <Building2 className="size-7 text-emerald-700" aria-hidden />
                  Contas
                </h1>
                <p className="mt-1 text-sm text-stone-500">
                  CRM · acesso real cruzado com contrato
                </p>
              </div>
              <nav className="flex gap-2 text-sm">
                <span className="rounded-lg bg-emerald-700 px-3 py-1.5 font-semibold text-white">
                  Contas
                </span>
                <Link
                  href="/dashboard/crm/tracking"
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 font-medium text-slate-700 hover:bg-slate-50"
                >
                  Funil
                </Link>
              </nav>
            </div>
          </header>

          <div className="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
            <label className="flex items-center gap-2 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Sistema
              </span>
              <select
                value={sistema}
                onChange={(e) => setSistema(e.target.value)}
                className="rounded-md border border-slate-200 px-2 py-1 text-sm"
              >
                <option value="">Todos</option>
                {(sistema && !sistemasOpts.includes(sistema)
                  ? [sistema, ...sistemasOpts]
                  : sistemasOpts.length
                    ? sistemasOpts
                    : ['inove4us-school', 'inove4us']
                ).map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Contrato
              </span>
              <select
                value={comContrato}
                onChange={(e) => setComContrato(e.target.value)}
                className="rounded-md border border-slate-200 px-2 py-1 text-sm"
              >
                <option value="">Todos</option>
                <option value="true">Com contrato</option>
                <option value="false">Sem contrato</option>
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Sem acesso desde
              </span>
              <select
                value={semAcesso}
                onChange={(e) => setSemAcesso(e.target.value)}
                className="rounded-md border border-slate-200 px-2 py-1 text-sm"
              >
                <option value="">—</option>
                <option value="7">7 dias</option>
                <option value="30">30 dias</option>
              </select>
            </label>
            {elapsedMs != null ? (
              <span className="ml-auto text-xs text-slate-400">{elapsedMs} ms</span>
            ) : null}
          </div>

          {error ? (
            <p className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              {error}
            </p>
          ) : null}

          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2 font-semibold">Conta</th>
                  <th className="px-3 py-2 font-semibold">Sistemas</th>
                  <th className="px-3 py-2 font-semibold">Último acesso</th>
                  <th className="px-3 py-2 font-semibold">Último login</th>
                  <th className="px-3 py-2 font-semibold">Sessões 7d / 30d</th>
                  <th className="px-3 py-2 font-semibold">Usuários 30d</th>
                  <th className="px-3 py-2 font-semibold">Contrato</th>
                  <th className="px-3 py-2 font-semibold">Plano</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={8} className="px-3 py-8 text-center text-slate-400">
                      <Loader2 className="mx-auto size-5 animate-spin" aria-hidden />
                    </td>
                  </tr>
                ) : contas.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-3 py-8 text-center text-slate-400">
                      Nenhuma conta neste recorte.
                    </td>
                  </tr>
                ) : (
                  contas.map((c) => {
                    const nunca = c.tem_contrato && !c.ultimo_acesso;
                    const parado = diasDesde(c.ultimo_acesso) != null && diasDesde(c.ultimo_acesso)! >= 7;
                    const rowClass = nunca
                      ? 'bg-amber-50 hover:bg-amber-100'
                      : parado
                        ? 'bg-slate-100 hover:bg-slate-200'
                        : 'hover:bg-emerald-50/60';
                    return (
                      <tr
                        key={c.instituicao_id}
                        className={`cursor-pointer border-t border-slate-100 ${rowClass}`}
                        onClick={() => router.push(`/dashboard/crm/contas/${c.instituicao_id}`)}
                      >
                        <td className="px-3 py-2">
                          <div className="font-semibold text-stone-900">{c.nome}</div>
                          <div className="font-mono text-[11px] text-slate-400">{c.instituicao_id}</div>
                          {nunca ? (
                            <span className="mt-1 inline-block rounded bg-amber-200 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-900">
                              Contratou e não acessou
                            </span>
                          ) : null}
                          {parado && !nunca ? (
                            <span className="mt-1 inline-block rounded bg-slate-300 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-slate-700">
                              Parado
                            </span>
                          ) : null}
                        </td>
                        <td className="px-3 py-2 text-xs">{(c.sistemas || []).join(', ') || '—'}</td>
                        <td className="px-3 py-2 whitespace-nowrap">{formatSp(c.ultimo_acesso)}</td>
                        <td className="px-3 py-2 whitespace-nowrap">{formatSp(c.ultimo_login)}</td>
                        <td className="px-3 py-2">
                          {c.sessoes_7d} / {c.sessoes_30d}
                        </td>
                        <td className="px-3 py-2">{c.usuarios_30d}</td>
                        <td className="px-3 py-2">
                          {c.tem_contrato ? (
                            <span className="font-medium text-emerald-800">
                              {c.contrato_status || 'sim'}
                            </span>
                          ) : (
                            <span className="text-slate-400">não</span>
                          )}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs">{c.plano || '—'}</td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </CrmContasGate>
  );
}
