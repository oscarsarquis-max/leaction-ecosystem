'use client';

import Link from 'next/link';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { FormEvent, Suspense, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Loader2, Lock } from 'lucide-react';
import { useAuthGate } from '@/lib/require-hub-login';

function formatSp(iso: string | null | undefined) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
  } catch {
    return '—';
  }
}

function formatDay(isoDate: string) {
  try {
    return new Date(`${isoDate}T12:00:00Z`).toLocaleDateString('pt-BR', {
      timeZone: 'UTC',
      day: '2-digit',
      month: '2-digit',
    });
  } catch {
    return isoDate;
  }
}

function dadosCompactos(dados: Record<string, unknown> | null | undefined) {
  if (!dados || typeof dados !== 'object') return '';
  return Object.entries(dados)
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
    .join(' · ');
}

function toIso(value: string) {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toISOString();
}

type PessoaAtividade = {
  usuario_origem_ref: string;
  sistema_origem: string | null;
  papel: string | null;
  primeiro_acesso: string | null;
  ultimo_acesso: string | null;
  ultimo_login: string | null;
  sessoes: number;
  eventos_total: number;
  eventos_por_tipo: Record<string, number>;
  ultimo_evento: { tipo: string; quando: string | null } | null;
};

type Linha = {
  quando: string | null;
  sistema: string | null;
  usuario_origem_ref: string | null;
  papel: string | null;
  tipo: string;
  dados: Record<string, unknown>;
  id_sessao: string;
};

type PorDia = {
  data: string;
  eventos: number;
  pessoas_ativas: number;
  por_tipo: Record<string, number>;
};

type AtividadePayload = {
  ok: boolean;
  instituicao_id: string;
  pessoas: PessoaAtividade[];
  linha_do_tempo: Linha[];
  por_dia: PorDia[];
  sinais: {
    convites: { enviados: number; aceitos: number; convite_id: string[] };
    professores_sem_atividade_apos_aceite: Array<{
      usuario_origem_ref: string;
      sistema_origem: string | null;
      papel: string | null;
      aceite_em: string | null;
    }>;
    horas_aceite_ate_primeiro_uso: Array<{
      usuario_origem_ref: string;
      sistema_origem: string | null;
      papel: string | null;
      aceite_em: string | null;
      primeiro_uso_em: string | null;
      primeiro_uso_tipo: string;
      horas: number;
    }>;
    parados_ha_dias: Array<{
      usuario_origem_ref: string;
      sistema_origem: string | null;
      papel: string | null;
      ultimo_acesso: string | null;
    }>;
  };
  meta: {
    desde: string;
    ate: string | null;
    limite: number;
    retornados: number;
    tem_mais: boolean;
    parado_dias: number;
    elapsed_ms: number;
  };
};

function chipsOf(mapa: Record<string, number>) {
  return Object.entries(mapa)
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([tipo, n]) => `${tipo} ${n}`)
    .join(' · ');
}

function AtividadeInner() {
  const params = useParams<{ instituicao_id: string }>();
  const router = useRouter();
  const search = useSearchParams();
  const id = String(params?.instituicao_id || '').trim();
  const { hydrated, isAuthenticated, requireLogin } = useAuthGate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState<AtividadePayload | null>(null);

  const pessoa = search.get('pessoa') || '';
  const sistema = search.get('sistema') || '';
  const tipo = search.get('tipo') || '';
  const desde = search.get('desde') || '';
  const ate = search.get('ate') || '';
  const limite = Math.min(1000, Math.max(1, Number(search.get('limite') || 200) || 200));

  const queryString = useMemo(() => {
    const qs = new URLSearchParams();
    if (pessoa) qs.set('pessoa', pessoa);
    if (sistema) qs.set('sistema', sistema);
    if (tipo) qs.set('tipo', tipo);
    if (desde) qs.set('desde', desde);
    if (ate) qs.set('ate', ate);
    qs.set('limite', String(limite));
    return qs.toString();
  }, [pessoa, sistema, tipo, desde, ate, limite]);

  useEffect(() => {
    if (!hydrated) return;
    if (!isAuthenticated) {
      requireLogin(
        `/dashboard/crm/contas/${id}/atividade`,
        'Faça login para acessar a atividade do Sponge.'
      );
    }
  }, [hydrated, isAuthenticated, requireLogin, id]);

  useEffect(() => {
    if (!hydrated || !isAuthenticated || !id) return;
    let cancelled = false;
    setLoading(true);
    setError('');
    fetch(`/api/crm/contas/${encodeURIComponent(id)}/atividade?${queryString}`, {
      cache: 'no-store',
    })
      .then(async (res) => {
        const json = await res.json().catch(() => ({}));
        if (!res.ok || !json?.ok) {
          throw new Error(json?.error || `HTTP ${res.status}`);
        }
        if (!cancelled) setData(json as AtividadePayload);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Falha ao carregar atividade');
          setData(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [hydrated, isAuthenticated, id, queryString]);

  function pushFilters(next: Record<string, string>) {
    const qs = new URLSearchParams();
    const merged = {
      pessoa,
      sistema,
      tipo,
      desde,
      ate,
      limite: String(limite),
      ...next,
    };
    for (const [k, v] of Object.entries(merged)) {
      if (v) qs.set(k, v);
    }
    router.replace(`/dashboard/crm/contas/${id}/atividade?${qs.toString()}`);
  }

  function onFilterSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    pushFilters({
      pessoa: String(form.get('pessoa') || '').trim(),
      sistema: String(form.get('sistema') || '').trim(),
      tipo: String(form.get('tipo') || '').trim(),
      desde: toIso(String(form.get('desde') || '').trim()),
      ate: toIso(String(form.get('ate') || '').trim()),
      limite: '200',
    });
  }

  const maxEventosDia = Math.max(1, ...(data?.por_dia || []).map((d) => d.eventos));
  const maxPessoasDia = Math.max(1, ...(data?.por_dia || []).map((d) => d.pessoas_ativas));
  const tiposFiltro = useMemo(() => {
    const set = new Set<string>();
    for (const p of data?.pessoas || []) {
      for (const t of Object.keys(p.eventos_por_tipo || {})) set.add(t);
    }
    return [...set].sort();
  }, [data]);

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
          href={`/dashboard/crm/contas/${id}`}
          className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-emerald-800"
        >
          <ArrowLeft className="size-4" aria-hidden />
          Ficha da conta
        </Link>

        {loading && !data ? (
          <div className="flex justify-center py-16 text-slate-400">
            <Loader2 className="size-6 animate-spin" aria-hidden />
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {error}
          </div>
        ) : data ? (
          <>
            <header className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h1 className="text-2xl font-bold text-stone-900">Atividade</h1>
              <p className="mt-1 font-mono text-xs text-slate-400">{data.instituicao_id}</p>
              <p className="mt-2 text-sm text-slate-600">
                Desde {formatSp(data.meta.desde)}
                {data.meta.ate ? ` até ${formatSp(data.meta.ate)}` : ''}
                {` · ${data.meta.elapsed_ms} ms`}
              </p>
            </header>

            <section className="mb-6 overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
              <h2 className="border-b border-slate-100 px-4 py-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                Pessoas
              </h2>
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Papel</th>
                    <th className="px-3 py-2">Identificador</th>
                    <th className="px-3 py-2">Primeiro acesso</th>
                    <th className="px-3 py-2">Último acesso</th>
                    <th className="px-3 py-2">Último login</th>
                    <th className="px-3 py-2">Sessões</th>
                    <th className="px-3 py-2">Eventos</th>
                    <th className="px-3 py-2">Tipos</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.pessoas || []).length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-3 py-6 text-center text-slate-400">
                        Nenhuma pessoa identificada.
                      </td>
                    </tr>
                  ) : (
                    data.pessoas.map((p) => {
                      const selected =
                        pessoa === p.usuario_origem_ref &&
                        (!sistema || sistema === (p.sistema_origem || ''));
                      return (
                        <tr
                          key={`${p.usuario_origem_ref}:${p.sistema_origem || ''}`}
                          className={`cursor-pointer border-t border-slate-100 ${selected ? 'bg-slate-100' : 'hover:bg-slate-50'}`}
                          onClick={() =>
                            pushFilters({
                              pessoa: p.usuario_origem_ref,
                              sistema: p.sistema_origem || '',
                              limite: '200',
                            })
                          }
                        >
                          <td className="px-3 py-2">{p.papel || '—'}</td>
                          <td className="px-3 py-2 font-mono text-xs">{p.usuario_origem_ref}</td>
                          <td className="whitespace-nowrap px-3 py-2">{formatSp(p.primeiro_acesso)}</td>
                          <td className="whitespace-nowrap px-3 py-2">{formatSp(p.ultimo_acesso)}</td>
                          <td className="whitespace-nowrap px-3 py-2">{formatSp(p.ultimo_login)}</td>
                          <td className="px-3 py-2">{p.sessoes}</td>
                          <td className="px-3 py-2">{p.eventos_total}</td>
                          <td className="px-3 py-2 text-xs text-slate-600">
                            {chipsOf(p.eventos_por_tipo) || '—'}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </section>

            <section className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                Ritmo
              </h2>
              <p className="mb-3 text-xs text-slate-500">Barras: eventos (claro) e pessoas ativas (escuro).</p>
              <div className="flex h-40 items-end gap-1 overflow-x-auto pb-6">
                {(data.por_dia || []).map((d) => (
                  <div key={d.data} className="flex min-w-[18px] flex-1 flex-col items-center gap-1">
                    <div className="flex h-28 w-full items-end justify-center gap-px">
                      <div
                        className="w-2 bg-slate-400"
                        style={{ height: `${Math.max(2, (d.eventos / maxEventosDia) * 100)}%` }}
                        title={`${d.data}: ${d.eventos} eventos`}
                      />
                      <div
                        className="w-2 bg-slate-700"
                        style={{ height: `${Math.max(2, (d.pessoas_ativas / maxPessoasDia) * 100)}%` }}
                        title={`${d.data}: ${d.pessoas_ativas} pessoas`}
                      />
                    </div>
                    <span className="rotate-45 text-[9px] text-slate-400">{formatDay(d.data)}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                Linha do tempo
              </h2>
              <form className="mb-4 grid gap-2 text-sm md:grid-cols-6" onSubmit={onFilterSubmit}>
                <label className="flex flex-col gap-1">
                  Pessoa
                  <input
                    name="pessoa"
                    defaultValue={pessoa}
                    className="rounded border border-slate-200 px-2 py-1 font-mono text-xs"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  Sistema
                  <input
                    name="sistema"
                    defaultValue={sistema}
                    className="rounded border border-slate-200 px-2 py-1 text-xs"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  Tipo
                  <input
                    name="tipo"
                    defaultValue={tipo}
                    list="tipos-atividade"
                    className="rounded border border-slate-200 px-2 py-1 font-mono text-xs"
                  />
                  <datalist id="tipos-atividade">
                    {tiposFiltro.map((t) => (
                      <option key={t} value={t} />
                    ))}
                  </datalist>
                </label>
                <label className="flex flex-col gap-1">
                  Desde
                  <input
                    name="desde"
                    type="datetime-local"
                    defaultValue={desde ? desde.slice(0, 16) : ''}
                    className="rounded border border-slate-200 px-2 py-1 text-xs"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  Até
                  <input
                    name="ate"
                    type="datetime-local"
                    defaultValue={ate ? ate.slice(0, 16) : ''}
                    className="rounded border border-slate-200 px-2 py-1 text-xs"
                  />
                </label>
                <div className="flex items-end gap-2">
                  <button
                    type="submit"
                    className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm font-semibold"
                  >
                    Filtrar
                  </button>
                  <button
                    type="button"
                    className="rounded-lg px-3 py-1.5 text-sm text-slate-500 underline"
                    onClick={() => router.replace(`/dashboard/crm/contas/${id}/atividade`)}
                  >
                    Limpar
                  </button>
                </div>
              </form>
              <ol className="space-y-2">
                {(data.linha_do_tempo || []).map((item, index) => (
                  <li
                    key={`${item.id_sessao}:${item.quando}:${item.tipo}:${index}`}
                    className="rounded-lg border border-slate-100 px-3 py-2 text-sm"
                  >
                    <div className="flex flex-wrap gap-x-3 gap-y-1">
                      <span className="whitespace-nowrap text-slate-500">{formatSp(item.quando)}</span>
                      <span>
                        {item.papel || '—'} ·{' '}
                        <span className="font-mono text-xs">{item.usuario_origem_ref || '—'}</span>
                      </span>
                      <span className="font-mono text-xs">{item.tipo}</span>
                    </div>
                    {dadosCompactos(item.dados) ? (
                      <p className="mt-1 font-mono text-[11px] text-slate-500">
                        {dadosCompactos(item.dados)}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ol>
              {data.meta.tem_mais && limite < 1000 ? (
                <button
                  type="button"
                  className="mt-4 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold"
                  onClick={() => pushFilters({ limite: String(Math.min(1000, limite + 200)) })}
                >
                  Carregar mais
                </button>
              ) : null}
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                Sinais
              </h2>
              <dl className="grid gap-4 text-sm md:grid-cols-2">
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">Convites</dt>
                  <dd>
                    enviados {data.sinais.convites.enviados} · aceitos {data.sinais.convites.aceitos}
                  </dd>
                  <details className="mt-1">
                    <summary className="cursor-pointer text-xs text-slate-500">
                      Sem aceite correspondente ({data.sinais.convites.convite_id.length})
                    </summary>
                    <ul className="mt-1 font-mono text-xs">
                      {data.sinais.convites.convite_id.map((cid) => (
                        <li key={cid}>{cid}</li>
                      ))}
                    </ul>
                  </details>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">
                    Sem atividade após aceite
                  </dt>
                  <dd>{data.sinais.professores_sem_atividade_apos_aceite.length}</dd>
                  <details className="mt-1">
                    <summary className="cursor-pointer text-xs text-slate-500">Lista</summary>
                    <ul className="mt-1 text-xs">
                      {data.sinais.professores_sem_atividade_apos_aceite.map((p) => (
                        <li key={p.usuario_origem_ref} className="font-mono">
                          {p.papel} · {p.usuario_origem_ref} · {formatSp(p.aceite_em)}
                        </li>
                      ))}
                    </ul>
                  </details>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">
                    Horas aceite → primeiro uso
                  </dt>
                  <dd>{data.sinais.horas_aceite_ate_primeiro_uso.length}</dd>
                  <details className="mt-1">
                    <summary className="cursor-pointer text-xs text-slate-500">Lista</summary>
                    <ul className="mt-1 text-xs">
                      {data.sinais.horas_aceite_ate_primeiro_uso.map((p) => (
                        <li key={p.usuario_origem_ref} className="font-mono">
                          {p.papel} · {p.usuario_origem_ref} · {p.horas} h · {p.primeiro_uso_tipo}
                        </li>
                      ))}
                    </ul>
                  </details>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-400">
                    Parados há mais de {data.meta.parado_dias} dias
                  </dt>
                  <dd>{data.sinais.parados_ha_dias.length}</dd>
                  <details className="mt-1">
                    <summary className="cursor-pointer text-xs text-slate-500">Lista</summary>
                    <ul className="mt-1 text-xs">
                      {data.sinais.parados_ha_dias.map((p) => (
                        <li key={`${p.usuario_origem_ref}:${p.sistema_origem || ''}`} className="font-mono">
                          {p.papel} · {p.usuario_origem_ref} · {formatSp(p.ultimo_acesso)}
                        </li>
                      ))}
                    </ul>
                  </details>
                </div>
              </dl>
            </section>
          </>
        ) : null}
      </div>
    </div>
  );
}

export default function CrmContaAtividadePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[50vh] items-center justify-center bg-stone-50 text-stone-500">
          <Loader2 className="size-5 animate-spin" aria-hidden />
        </div>
      }
    >
      <AtividadeInner />
    </Suspense>
  );
}
