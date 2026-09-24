'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Loader2, Lock } from 'lucide-react';
import { useAuthGate } from '@/lib/require-hub-login';

type FuncionalidadeUso = {
  chave: string;
  rotulo: string;
  sistema: string | null;
  eventos: number;
  pct_eventos: number;
  pessoas: number;
  pct_pessoas: number;
  sessoes: number;
  pct_sessoes: number;
  tempo_s: number;
  pct_tempo: number;
  tempo_medio_por_sessao_s: number;
};

type OutrosUso = FuncionalidadeUso & {
  tipos_frequentes?: Array<{ tipo_evento: string; count: number }>;
  paginas_frequentes?: Array<{ url: string; count: number }>;
};

type SeriePonto = {
  data: string;
  chave: string;
  rotulo: string;
  sistema: string | null;
  eventos: number;
  pessoas: number;
};

type UsoResponse = {
  ok?: boolean;
  error?: string;
  periodo?: { desde: string; ate: string };
  recorte?: {
    sistema: string | null;
    instituicao_id: string | null;
    usuario_origem_ref: string | null;
  };
  totais?: {
    eventos: number;
    pessoas: number;
    sessoes: number;
    tempo_s: number;
  };
  funcionalidades?: FuncionalidadeUso[];
  outros?: OutrosUso;
  serie?: SeriePonto[];
  meta?: { elapsed_ms?: number };
};

type ContaOpt = {
  instituicao_id: string;
  nome: string;
};

function todaySp(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' });
}

function daysAgoSp(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' });
}

function formatTempo(seconds: number): string {
  const n = Number(seconds) || 0;
  if (n <= 0) return '0s';
  if (n < 60) return `${n < 10 ? n.toFixed(1) : Math.round(n)}s`;
  const m = Math.floor(n / 60);
  const sec = Math.round(n % 60);
  if (m < 60) return sec ? `${m} min ${sec}s` : `${m} min`;
  const h = Math.floor(m / 60);
  const mm = m % 60;
  return mm ? `${h} h ${mm} min` : `${h} h`;
}

function sistemaLabel(s: string | null | undefined): string {
  if (s === 'inove4us') return 'Inove';
  if (s === 'inove4us-school') return 'School';
  return s || '—';
}

function featureId(f: { chave: string; sistema: string | null }): string {
  return `${f.chave}|${f.sistema || ''}`;
}

function RankBars({
  items,
  valueOf,
  labelOf,
  formatValue,
}: {
  items: FuncionalidadeUso[];
  valueOf: (f: FuncionalidadeUso) => number;
  labelOf: (f: FuncionalidadeUso) => string;
  formatValue: (f: FuncionalidadeUso) => string;
}) {
  const max = Math.max(1, ...items.map((i) => valueOf(i)));
  return (
    <ul className="space-y-2">
      {items.length === 0 ? (
        <li className="text-sm text-slate-400">sem dados no recorte</li>
      ) : (
        items.map((item) => {
          const pct = Math.max(0, Math.min(100, (valueOf(item) / max) * 100));
          return (
            <li key={featureId(item)}>
              <div className="mb-0.5 flex items-baseline justify-between gap-2 text-sm">
                <span className="truncate font-medium text-stone-800">{item.rotulo}</span>
                <span className="shrink-0 tabular-nums text-stone-600">{formatValue(item)}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-stone-100">
                <div
                  className="h-full rounded-full bg-emerald-500"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <p className="mt-0.5 text-[11px] text-slate-400">{labelOf(item)}</p>
            </li>
          );
        })
      )}
    </ul>
  );
}

export default function CrmUsoPage() {
  const router = useRouter();
  const { hydrated, isAuthenticated, requireLogin } = useAuthGate();
  const [desde, setDesde] = useState(() => daysAgoSp(30));
  const [ate, setAte] = useState(() => todaySp());
  const [sistema, setSistema] = useState('');
  const [instituicaoId, setInstituicaoId] = useState('');
  const [contas, setContas] = useState<ContaOpt[]>([]);
  const [data, setData] = useState<UsoResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<{ chave: string; sistema: string | null } | null>(
    null
  );
  const [serie, setSerie] = useState<SeriePonto[]>([]);
  const [serieLoading, setSerieLoading] = useState(false);

  useEffect(() => {
    if (!hydrated) return;
    if (!isAuthenticated) {
      requireLogin('/dashboard/crm/uso', 'Faça login para acessar o uso do Sponge.');
    }
  }, [hydrated, isAuthenticated, requireLogin]);

  useEffect(() => {
    if (!hydrated || !isAuthenticated) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch('/api/crm/contas', { cache: 'no-store' });
        const json = (await res.json()) as { contas?: Array<{ instituicao_id: string; nome: string }> };
        if (cancelled) return;
        const list = (json.contas || []).map((c) => ({
          instituicao_id: c.instituicao_id,
          nome: c.nome || c.instituicao_id,
        }));
        setContas(list);
      } catch {
        /* filtro por nome fica só com o que carregar */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [hydrated, isAuthenticated]);

  const loadUso = useCallback(async () => {
    setLoading(true);
    setError('');
    const qs = new URLSearchParams();
    if (desde) qs.set('desde', `${desde}T00:00:00-03:00`);
    if (ate) qs.set('ate', `${ate}T23:59:59.999-03:00`);
    if (sistema) qs.set('sistema', sistema);
    if (instituicaoId) qs.set('instituicao_id', instituicaoId);
    try {
      const res = await fetch(`/api/crm/uso?${qs.toString()}`, { cache: 'no-store' });
      const json = (await res.json()) as UsoResponse;
      if (!res.ok || json.ok === false) {
        setError(json.error || `Erro ${res.status}`);
        setData(null);
        return;
      }
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'falha ao carregar uso');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [desde, ate, sistema, instituicaoId]);

  useEffect(() => {
    if (!hydrated || !isAuthenticated) return;
    void loadUso();
  }, [hydrated, isAuthenticated, loadUso]);

  const loadSerie = useCallback(
    async (feat: { chave: string; sistema: string | null }) => {
      setSerieLoading(true);
      const qs = new URLSearchParams();
      qs.set('agrupar', 'dia');
      if (desde) qs.set('desde', `${desde}T00:00:00-03:00`);
      if (ate) qs.set('ate', `${ate}T23:59:59.999-03:00`);
      if (sistema) qs.set('sistema', sistema);
      if (instituicaoId) qs.set('instituicao_id', instituicaoId);
      if (feat.sistema) qs.set('sistema', feat.sistema);
      try {
        const res = await fetch(`/api/crm/uso?${qs.toString()}`, { cache: 'no-store' });
        const json = (await res.json()) as UsoResponse;
        const points = (json.serie || []).filter(
          (p) => p.chave === feat.chave && (p.sistema || '') === (feat.sistema || '')
        );
        setSerie(points);
      } catch {
        setSerie([]);
      } finally {
        setSerieLoading(false);
      }
    },
    [desde, ate, sistema, instituicaoId]
  );

  const ranking = data?.funcionalidades || [];
  const totais = data?.totais;
  const outros = data?.outros;
  const maxSerie = useMemo(
    () => Math.max(1, ...serie.map((p) => p.eventos)),
    [serie]
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
        <span className="flex size-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600 ring-1 ring-emerald-200">
          <Lock className="size-7" aria-hidden />
        </span>
        <h1 className="text-xl font-bold text-stone-900">Uso protegido</h1>
        <p className="max-w-md text-sm text-stone-500">
          O acompanhamento de uso do Action-Sponge só pode ser acessado com login no Action Hub.
        </p>
        <button
          type="button"
          onClick={() =>
            requireLogin('/dashboard/crm/uso', 'Faça login para acessar o uso do Sponge.')
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

  return (
    <div className="min-h-screen bg-stone-50 px-4 py-8 md:px-8">
      <div className="mx-auto max-w-6xl">
        <Link
          href="/"
          className="mb-3 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 transition hover:text-emerald-800"
        >
          <ArrowLeft className="size-4" aria-hidden />
          Voltar ao Action Hub
        </Link>
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-stone-900 md:text-3xl">
              Uso por funcionalidade
            </h1>
            <p className="mt-1 max-w-2xl text-sm text-stone-500">
              Incidência, alcance e tempo estimado por intervalo entre ações. Ausência de ação
              acima de 10 min não conta.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/dashboard/crm/pos-venda"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
            >
              Pós-venda
            </Link>
            <Link
              href="/dashboard/crm/contas"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
            >
              Contas
            </Link>
          </div>
        </div>

        <form
          className="mb-6 grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-5"
          onSubmit={(e) => {
            e.preventDefault();
            setSelected(null);
            setSerie([]);
            void loadUso();
          }}
        >
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Desde
            <input
              type="date"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm font-medium text-stone-800"
            />
          </label>
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Até
            <input
              type="date"
              value={ate}
              onChange={(e) => setAte(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm font-medium text-stone-800"
            />
          </label>
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Sistema
            <select
              value={sistema}
              onChange={(e) => setSistema(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm font-medium text-stone-800"
            >
              <option value="">Todos</option>
              <option value="inove4us">Inove</option>
              <option value="inove4us-school">School</option>
            </select>
          </label>
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Instituição
            <select
              value={instituicaoId}
              onChange={(e) => setInstituicaoId(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm font-medium text-stone-800"
            >
              <option value="">Todas</option>
              {contas.map((c) => (
                <option key={c.instituicao_id} value={c.instituicao_id}>
                  {c.nome}
                </option>
              ))}
            </select>
          </label>
          <div className="flex items-end">
            <button
              type="submit"
              className="w-full rounded-lg bg-emerald-500 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-600"
            >
              Aplicar
            </button>
          </div>
        </form>

        {error ? (
          <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        ) : null}

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Calculando uso…
          </div>
        ) : (
          <>
            {totais ? (
              <p className="mb-4 text-sm text-slate-500">
                {totais.eventos} eventos · {totais.pessoas} pessoas · {totais.sessoes} sessões ·{' '}
                {formatTempo(totais.tempo_s)} estimados
                {typeof data?.meta?.elapsed_ms === 'number'
                  ? ` · ${data.meta.elapsed_ms} ms`
                  : ''}
              </p>
            ) : null}

            <div className="mb-6 grid gap-4 lg:grid-cols-3">
              <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                  Por tempo
                </h2>
                <RankBars
                  items={ranking}
                  valueOf={(f) => f.tempo_s}
                  labelOf={(f) => `${f.pct_tempo}% do tempo · ${sistemaLabel(f.sistema)}`}
                  formatValue={(f) => formatTempo(f.tempo_s)}
                />
              </section>
              <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                  Por eventos
                </h2>
                <RankBars
                  items={[...ranking].sort((a, b) => b.eventos - a.eventos)}
                  valueOf={(f) => f.eventos}
                  labelOf={(f) => `${f.pct_eventos}% dos eventos · ${sistemaLabel(f.sistema)}`}
                  formatValue={(f) => String(f.eventos)}
                />
              </section>
              <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                  Por pessoas
                </h2>
                <RankBars
                  items={[...ranking].sort((a, b) => b.pessoas - a.pessoas || b.eventos - a.eventos)}
                  valueOf={(f) => f.pessoas}
                  labelOf={(f) => `${f.pct_pessoas}% das pessoas · ${sistemaLabel(f.sistema)}`}
                  formatValue={(f) => String(f.pessoas)}
                />
              </section>
            </div>

            <section className="mb-6 overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
              <h2 className="border-b border-slate-100 px-4 py-3 text-sm font-bold uppercase tracking-wide text-slate-500">
                Todas as funcionalidades
              </h2>
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Funcionalidade</th>
                    <th className="px-3 py-2">Sistema</th>
                    <th className="px-3 py-2">Eventos</th>
                    <th className="px-3 py-2">%</th>
                    <th className="px-3 py-2">Pessoas</th>
                    <th className="px-3 py-2">%</th>
                    <th className="px-3 py-2">Sessões</th>
                    <th className="px-3 py-2">%</th>
                    <th className="px-3 py-2">Tempo</th>
                    <th className="px-3 py-2">%</th>
                    <th className="px-3 py-2">Méd./sessão</th>
                  </tr>
                </thead>
                <tbody>
                  {ranking.map((f) => {
                    const active =
                      selected &&
                      selected.chave === f.chave &&
                      (selected.sistema || '') === (f.sistema || '');
                    return (
                      <tr
                        key={featureId(f)}
                        className={`cursor-pointer border-t border-slate-100 hover:bg-emerald-50/60 ${
                          active ? 'bg-emerald-50' : ''
                        }`}
                        onClick={() => {
                          setSelected({ chave: f.chave, sistema: f.sistema });
                          void loadSerie({ chave: f.chave, sistema: f.sistema });
                        }}
                      >
                        <td className="px-3 py-2 font-medium text-stone-800">{f.rotulo}</td>
                        <td className="px-3 py-2">{sistemaLabel(f.sistema)}</td>
                        <td className="px-3 py-2 tabular-nums">{f.eventos}</td>
                        <td className="px-3 py-2 tabular-nums">{f.pct_eventos}%</td>
                        <td className="px-3 py-2 tabular-nums">{f.pessoas}</td>
                        <td className="px-3 py-2 tabular-nums">{f.pct_pessoas}%</td>
                        <td className="px-3 py-2 tabular-nums">{f.sessoes}</td>
                        <td className="px-3 py-2 tabular-nums">{f.pct_sessoes}%</td>
                        <td className="px-3 py-2 tabular-nums">{formatTempo(f.tempo_s)}</td>
                        <td className="px-3 py-2 tabular-nums">{f.pct_tempo}%</td>
                        <td className="px-3 py-2 tabular-nums">
                          {formatTempo(f.tempo_medio_por_sessao_s)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </section>

            {selected ? (
              <section className="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">
                    Série por dia · {ranking.find((f) => f.chave === selected.chave && f.sistema === selected.sistema)?.rotulo || selected.chave}
                  </h2>
                  {instituicaoId ? (
                    <Link
                      href={`/dashboard/crm/contas/${encodeURIComponent(instituicaoId)}/atividade${
                        selected.sistema ? `?sistema=${encodeURIComponent(selected.sistema)}` : ''
                      }`}
                      className="text-sm font-medium text-emerald-700 hover:underline"
                    >
                      Ver atividade filtrada
                    </Link>
                  ) : (
                    <span className="text-xs text-slate-400">
                      Filtre por instituição para abrir a atividade.
                    </span>
                  )}
                </div>
                {serieLoading ? (
                  <p className="text-sm text-slate-400">carregando série…</p>
                ) : serie.length === 0 ? (
                  <p className="text-sm text-slate-400">sem pontos no período</p>
                ) : (
                  <ul className="space-y-1.5">
                    {serie.map((p) => (
                      <li key={p.data} className="flex items-center gap-3 text-sm">
                        <span className="w-24 shrink-0 tabular-nums text-slate-500">
                          {p.data}
                        </span>
                        <div className="h-3 flex-1 overflow-hidden rounded bg-stone-100">
                          <div
                            className="h-full rounded bg-emerald-400"
                            style={{ width: `${(p.eventos / maxSerie) * 100}%` }}
                          />
                        </div>
                        <span className="w-36 shrink-0 text-right tabular-nums text-stone-700">
                          {p.eventos} ev. · {p.pessoas} pess.
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            ) : (
              <p className="mb-6 text-sm text-slate-400">
                Clique numa funcionalidade para ver a tendência diária.
              </p>
            )}

            {outros && (outros.eventos > 0 || (outros.tipos_frequentes || []).length) ? (
              <section className="rounded-xl border border-amber-200 bg-amber-50/40 p-4 shadow-sm">
                <h2 className="mb-1 text-sm font-bold uppercase tracking-wide text-amber-800">
                  Não mapeado
                </h2>
                <p className="mb-3 text-sm text-amber-900/80">
                  {outros.eventos} eventos ({outros.pct_eventos}%) sem funcionalidade na taxonomia —
                  o que falta mapear em <code>crm-funcionalidades.js</code>.
                </p>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <h3 className="mb-1 text-xs font-semibold uppercase text-slate-500">
                      Tipos mais frequentes
                    </h3>
                    <ul className="text-sm">
                      {(outros.tipos_frequentes || []).map((t) => (
                        <li key={t.tipo_evento} className="flex justify-between gap-2">
                          <span className="font-mono text-xs">{t.tipo_evento}</span>
                          <span className="tabular-nums">{t.count}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h3 className="mb-1 text-xs font-semibold uppercase text-slate-500">
                      Páginas mais frequentes
                    </h3>
                    <ul className="text-sm">
                      {(outros.paginas_frequentes || []).map((p) => (
                        <li key={p.url} className="flex justify-between gap-2">
                          <span className="truncate font-mono text-xs">{p.url}</span>
                          <span className="tabular-nums">{p.count}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </section>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
