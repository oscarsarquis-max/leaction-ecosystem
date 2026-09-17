'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { ArrowLeft, Loader2, Lock } from 'lucide-react';
import { useAuthGate } from '@/lib/require-hub-login';

type Etapa = {
  feito: boolean;
  quando: string | null;
  dias_desde: number | null;
  fonte: string | null;
  quantidade?: number | null;
  quantidade_rotulo?: string | null;
};

type HistoricoItem = {
  n: number;
  chave: string;
  rotulo: string;
  feito: boolean;
  quando: string | null;
  dias_desde: number | null;
  fonte: string | null;
  quantidade?: number | null;
  quantidade_rotulo?: string | null;
};

type Professor = {
  convite_id: string | null;
  professor_id: string | null;
  usuario_origem_ref: string | null;
  nome: string | null;
  convidado_em: string | null;
  aceitou_em: string | null;
  primeiro_uso_em: string | null;
  ultimo_uso_em: string | null;
  dias_sem_uso: number | null;
};

type Detalhe = {
  ok?: boolean;
  error?: string;
  instituicao_id: string;
  nome: string;
  contratou_em: string | null;
  dias_de_contrato: number | null;
  etapa_atual: number;
  etapa_atual_rotulo?: string;
  etapas?: Record<string, Etapa>;
  professores?: { convidados: number; aceitos: number; usando: number };
  licencas?: { em_uso: number; total: number };
  alertas?: Array<{ chave: string; severidade: string; explicacao?: string }>;
  professores_detalhe?: Professor[];
  historico?: HistoricoItem[];
};

function formatSp(iso: string | null | undefined) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
  } catch {
    return '—';
  }
}

export default function CrmContaPosVendaPage() {
  const params = useParams<{ instituicao_id: string }>();
  const router = useRouter();
  const id = String(params?.instituicao_id || '').trim();
  const { hydrated, isAuthenticated, requireLogin } = useAuthGate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [data, setData] = useState<Detalhe | null>(null);

  useEffect(() => {
    if (!hydrated) return;
    if (!isAuthenticated) {
      requireLogin(
        `/dashboard/crm/contas/${id}/pos-venda`,
        'Faça login para acessar o pós-venda do Sponge.'
      );
    }
  }, [hydrated, isAuthenticated, requireLogin, id]);

  useEffect(() => {
    if (!hydrated || !isAuthenticated || !id) return;
    let cancelled = false;
    setLoading(true);
    setError('');
    fetch(`/api/crm/contas/${encodeURIComponent(id)}/pos-venda`, { cache: 'no-store' })
      .then(async (res) => {
        const json = (await res.json()) as Detalhe;
        if (!res.ok || json.ok === false) {
          throw new Error(json.error || `HTTP ${res.status}`);
        }
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
  }, [hydrated, isAuthenticated, id]);

  if (!hydrated) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center bg-stone-50 text-stone-500">
        <Loader2 className="size-5 animate-spin" aria-hidden />
      </div>
    );
  }
  if (!isAuthenticated) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 bg-stone-50">
        <Lock className="size-8 text-emerald-600" aria-hidden />
        <p className="text-sm text-stone-500">Login necessário.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <div className="mx-auto max-w-7xl px-4 py-8 md:px-6 md:py-10">
        <Link
          href="/dashboard/crm/pos-venda"
          className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-emerald-800"
        >
          <ArrowLeft className="size-4" aria-hidden />
          Pós-venda
        </Link>

        {loading ? (
          <div className="flex justify-center py-16 text-slate-400">
            <Loader2 className="size-6 animate-spin" aria-hidden />
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {error}
            <button type="button" className="ml-3 underline" onClick={() => router.push('/dashboard/crm/pos-venda')}>
              Voltar
            </button>
          </div>
        ) : data ? (
          <>
            <header className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h1 className="text-2xl font-bold text-stone-900">{data.nome}</h1>
              <p className="mt-1 font-mono text-xs text-slate-400">{data.instituicao_id}</p>
              <p className="mt-2 text-sm text-slate-600">
                Etapa {data.etapa_atual}/9 · {data.etapa_atual_rotulo || '—'}
                {data.historico?.find((h) => h.n === data.etapa_atual)?.quantidade_rotulo
                  ? ` · ${data.historico.find((h) => h.n === data.etapa_atual)?.quantidade_rotulo}`
                  : ''}{' '}
                · contrato há {data.dias_de_contrato ?? '—'} dia(s)
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Link
                  href={`/dashboard/crm/contas/${encodeURIComponent(id)}`}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold"
                >
                  Ficha
                </Link>
                <Link
                  href={`/dashboard/crm/contas/${encodeURIComponent(id)}/atividade`}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold"
                >
                  Atividade
                </Link>
                <Link
                  href={`/dashboard/crm/uso?instituicao_id=${encodeURIComponent(id)}`}
                  className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-sm font-semibold text-emerald-800"
                >
                  Uso
                </Link>
              </div>
            </header>

            <section className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                Linha do tempo
              </h2>
              <ol className="space-y-2">
                {(data.historico || []).map((h) => (
                  <li key={h.chave} className="flex flex-wrap items-baseline gap-2 text-sm">
                    <span
                      className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                        h.feito ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-500'
                      }`}
                    >
                      {h.n}
                    </span>
                    <span className="font-medium">{h.rotulo}</span>
                    {h.quantidade_rotulo ? (
                      <span className="text-slate-500">{h.quantidade_rotulo}</span>
                    ) : null}
                    <span className="text-slate-500">
                      {h.feito ? formatSp(h.quando) : 'não feita'}
                      {h.dias_desde != null ? ` · ${h.dias_desde}d` : ''}
                      {h.fonte ? ` · ${h.fonte}` : ''}
                    </span>
                  </li>
                ))}
              </ol>
            </section>

            <section className="mb-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                Professores
              </h2>
              <p className="mb-3 text-sm text-slate-500">
                {data.professores?.convidados ?? 0} convidados · {data.professores?.aceitos ?? 0}{' '}
                aceitos · {data.professores?.usando ?? 0} usando · licenças{' '}
                {data.licencas?.em_uso ?? 0}/{data.licencas?.total ?? 0}
              </p>
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="text-xs uppercase text-slate-400">
                    <tr>
                      <th className="py-2 pr-3">Professor</th>
                      <th className="py-2 pr-3">Convidado</th>
                      <th className="py-2 pr-3">Aceitou</th>
                      <th className="py-2 pr-3">Primeiro uso</th>
                      <th className="py-2 pr-3">Último uso</th>
                      <th className="py-2">Dias sem uso</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.professores_detalhe || []).length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-4 text-slate-400">
                          sem eventos de convite no Sponge — contagens vêm do snapshot
                        </td>
                      </tr>
                    ) : (
                      (data.professores_detalhe || []).map((p, idx) => (
                        <tr key={p.convite_id || p.usuario_origem_ref || String(idx)} className="border-t border-slate-100">
                          <td className="py-2 pr-3">
                            {p.nome || p.usuario_origem_ref || p.convite_id || '—'}
                          </td>
                          <td className="py-2 pr-3">{formatSp(p.convidado_em)}</td>
                          <td className="py-2 pr-3">{formatSp(p.aceitou_em)}</td>
                          <td className="py-2 pr-3">{formatSp(p.primeiro_uso_em)}</td>
                          <td className="py-2 pr-3">{formatSp(p.ultimo_uso_em)}</td>
                          <td className="py-2 tabular-nums">{p.dias_sem_uso ?? '—'}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                Alertas
              </h2>
              {(data.alertas || []).length === 0 ? (
                <p className="text-sm text-slate-400">nenhum alerta no limiar atual</p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {(data.alertas || []).map((a) => (
                    <li key={a.chave + (a.explicacao || '')}>
                      <span
                        className={`mr-2 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                          a.severidade === 'alta'
                            ? 'bg-red-50 text-red-800'
                            : 'bg-amber-50 text-amber-900'
                        }`}
                      >
                        {a.chave}
                      </span>
                      {a.explicacao}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        ) : null}
      </div>
    </div>
  );
}
