'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, Loader2, Sparkles } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import {
  discardCmsSugestao,
  fetchCmsSugestaoRodada,
  fetchCmsSugestaoRodadaAtual,
  fetchCmsSugestoes,
  generateCmsSugestoes,
  publishCmsSugestao,
  type CmsSugestaoPair,
  type CmsSugestaoRodada,
  type CmsSugestoesGrupoDia,
} from '@/lib/admin-api';

const field =
  'w-full rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm text-stone-900 outline-none ring-emerald-400 focus:ring-2';

const TIPO_STYLE: Record<string, { label: string; className: string }> = {
  noticia: { label: 'Notícia', className: 'bg-blue-50 text-blue-800 ring-blue-200' },
  evento: { label: 'Evento', className: 'bg-rose-50 text-rose-800 ring-rose-200' },
  curiosidade: { label: 'Curiosidade', className: 'bg-lime-50 text-lime-800 ring-lime-200' },
};

type Draft = {
  titulo_pt: string;
  resumo_pt: string;
  markdown_pt: string;
  titulo_en: string;
  resumo_en: string;
  markdown_en: string;
};

function draftFrom(pair: CmsSugestaoPair): Draft {
  return {
    titulo_pt: pair.pt?.titulo || '',
    resumo_pt: pair.pt?.resumo || '',
    markdown_pt: pair.pt?.conteudo_html || '',
    titulo_en: pair.en?.titulo || '',
    resumo_en: pair.en?.resumo || '',
    markdown_en: pair.en?.conteudo_html || '',
  };
}

function Counter({ value, max }: { value: string; max: number }) {
  const n = [...value].length;
  return (
    <span className={`text-[11px] font-semibold ${n > max ? 'text-red-600' : 'text-stone-400'}`}>
      {n}/{max}
    </span>
  );
}

function apiErrorMessage(err: unknown, fallback: string) {
  if (err && typeof err === 'object' && 'response' in err) {
    const data = (err as { response?: { data?: { error?: string; message?: string } } }).response
      ?.data;
    if (data?.error) return data.error;
    if (data?.message) return data.message;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

/** "25/11, 07:02" em America/Sao_Paulo. */
function formatSugestaoStamp(iso: string | null | undefined) {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  const parts = new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/Sao_Paulo',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)?.value || '';
  return `${get('day')}/${get('month')}, ${get('hour')}:${get('minute')}`;
}

/** "24/11" a partir de AAAA-MM-DD. */
function formatDiaCurto(value: string | null | undefined) {
  if (!value) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!m) return value;
  return `${m[3]}/${m[2]}`;
}

function horasRestantes(expiraIso: string | null | undefined, now = new Date()) {
  if (!expiraIso) return null;
  const end = new Date(expiraIso);
  if (Number.isNaN(end.getTime())) return null;
  const h = Math.ceil((end.getTime() - now.getTime()) / (60 * 60 * 1000));
  return h > 0 ? h : 0;
}

function labelGrupoDia(data: string, hoje: boolean, now = new Date()) {
  if (hoje) return 'Hoje';
  const ontem = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  const y = ontem.toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' });
  if (data === y) return 'Ontem';
  return formatDiaCurto(data) || data;
}

function progressLine(rodada: CmsSugestaoRodada | null) {
  if (!rodada?.progress) return 'Gerando…';
  const p = rodada.progress;
  if (p.message) return p.message;
  return `Lendo fontes… ${p.materias ?? 0} matérias · ${p.com_texto ?? 0} com texto · ${p.aprovadas ?? 0} aprovadas`;
}

function resultSummary(rodada: CmsSugestaoRodada) {
  const r = rodada.result;
  if (!r) return null;
  const parts: string[] = [];
  parts.push(`${r.created ?? 0} sugestões novas`);
  if (r.discarded_summary?.length) {
    parts.push(`${r.discarded_summary.length} descartes: ${r.discarded_summary.join(', ')}`);
  }
  if (r.shortfall_message) parts.push(r.shortfall_message);
  if (r.skipped === 'cap_atingido') parts.push('Limite diário de 5 já atingido.');
  return parts.join(' · ');
}

export function CmsSugestoes() {
  const { token } = useHubSession();
  const [rows, setRows] = useState<CmsSugestaoPair[]>([]);
  const [grupos, setGrupos] = useState<CmsSugestoesGrupoDia[]>([]);
  const [pendingToday, setPendingToday] = useState(0);
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [generating, setGenerating] = useState(false);
  const [rodada, setRodada] = useState<CmsSugestaoRodada | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCmsSugestoes(token);
      setRows(data.sugestoes);
      setGrupos(data.grupos);
      setPendingToday(data.pending_today_count);
      const next: Record<number, Draft> = {};
      for (const pair of data.sugestoes) next[pair.grupo_id] = draftFrom(pair);
      setDrafts(next);
    } catch {
      setError('Não foi possível carregar as sugestões.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  const watchRodada = useCallback(
    (id: number) => {
      if (!token) return;
      stopPoll();
      setGenerating(true);
      const tick = async () => {
        try {
          const current = await fetchCmsSugestaoRodada(token, id);
          setRodada(current);
          if (current.status === 'running') return;
          stopPoll();
          setGenerating(false);
          if (current.status === 'done') {
            setInfo(resultSummary(current) || 'Rodada concluída.');
            setError(null);
            await load();
          } else if (current.status === 'error') {
            setError(current.error?.message || 'Não foi possível gerar agora.');
            setInfo(null);
          }
        } catch (err) {
          stopPoll();
          setGenerating(false);
          setError(apiErrorMessage(err, 'Falha ao acompanhar a rodada.'));
        }
      };
      void tick();
      pollRef.current = setInterval(() => void tick(), 3000);
    },
    [token, stopPoll, load]
  );

  useEffect(() => {
    void load();
    return () => stopPoll();
  }, [load, stopPoll]);

  useEffect(() => {
    if (!token) return;
    void (async () => {
      try {
        const running = await fetchCmsSugestaoRodadaAtual(token);
        if (running?.status === 'running') {
          setRodada(running);
          watchRodada(running.id);
        }
      } catch {
        /* ignore */
      }
    })();
  }, [token, watchRodada]);

  function updateDraft(id: number, key: keyof Draft, value: string) {
    setDrafts((current) => ({
      ...current,
      [id]: { ...current[id], [key]: value },
    }));
  }

  async function onPublish(pair: CmsSugestaoPair) {
    if (!token) return;
    const draft = drafts[pair.grupo_id] || draftFrom(pair);
    setBusyId(pair.grupo_id);
    setError(null);
    setInfo(null);
    try {
      await publishCmsSugestao(token, pair.grupo_id, draft);
      setInfo('Sugestão publicada em PT e EN.');
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível publicar.'));
    } finally {
      setBusyId(null);
    }
  }

  async function onDiscard(pair: CmsSugestaoPair) {
    if (!token) return;
    setBusyId(pair.grupo_id);
    setError(null);
    setInfo(null);
    try {
      await discardCmsSugestao(token, pair.grupo_id);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível descartar.'));
    } finally {
      setBusyId(null);
    }
  }

  async function onGenerate() {
    if (!token) return;
    setError(null);
    setInfo(null);
    setGenerating(true);
    try {
      const started = await generateCmsSugestoes(token);
      setRodada({
        id: started.rodada_id,
        status: 'running',
        progress: { message: started.reused ? 'Retomando a rodada em andamento…' : 'Iniciando…' },
      });
      watchRodada(started.rodada_id);
    } catch (err) {
      setGenerating(false);
      setError(apiErrorMessage(err, 'Não foi possível gerar agora.'));
    }
  }

  const byId = useMemo(() => new Map(rows.map((r) => [r.grupo_id, r])), [rows]);
  const sections = useMemo(() => {
    if (grupos.length) {
      return grupos
        .map((g) => ({
          key: g.data,
          title: labelGrupoDia(g.data, g.hoje),
          pairs: g.grupo_ids.map((id) => byId.get(id)).filter(Boolean) as CmsSugestaoPair[],
        }))
        .filter((s) => s.pairs.length);
    }
    return rows.length ? [{ key: 'todas', title: 'Pendentes', pairs: rows }] : [];
  }, [grupos, rows, byId]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link
            href="/dashboard/cms"
            className="mb-2 inline-flex items-center gap-1 text-sm font-semibold text-stone-500 hover:text-stone-800"
          >
            <ArrowLeft className="size-4" aria-hidden />
            CMS
          </Link>
          <div className="mb-1 flex items-center gap-2">
            <Sparkles className="size-5 text-emerald-500" aria-hidden />
            <h1 className="text-xl font-bold text-stone-900">Sugestões do dia</h1>
          </div>
          <p className="max-w-xl text-sm text-stone-500">
            Gere sob demanda a partir dos feeds. Nada vai ao ar sem a sua aprovação.
            {pendingToday > 0 ? ` Pendentes de hoje: ${pendingToday}.` : null}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void onGenerate()}
          disabled={generating}
          className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-emerald-400 disabled:opacity-60"
        >
          {generating ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Sparkles className="size-4" aria-hidden />}
          Gerar sugestões
        </button>
      </div>

      {generating && rodada?.status === 'running' ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          <span className="inline-flex items-center gap-2 font-semibold">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            {progressLine(rodada)}
          </span>
        </div>
      ) : null}

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      ) : null}
      {info ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{info}</div>
      ) : null}

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-stone-500">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Carregando…
        </div>
      ) : sections.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-stone-300 bg-white px-5 py-8 text-sm text-stone-500">
          Nenhuma sugestão pendente. Use “Gerar sugestões”.
        </div>
      ) : (
        <div className="space-y-8">
          {sections.map((section) => (
            <section key={section.key} className="space-y-3">
              <h2 className="text-sm font-bold uppercase tracking-wider text-stone-500">{section.title}</h2>
              <div className="space-y-4">
                {section.pairs.map((pair) => {
                  const draft = drafts[pair.grupo_id] || draftFrom(pair);
                  const tipo = TIPO_STYLE[pair.tipo || ''] || {
                    label: pair.tipo || 'Item',
                    className: 'bg-stone-100 text-stone-700 ring-stone-200',
                  };
                  const busy = busyId === pair.grupo_id;
                  const sugerida = formatSugestaoStamp(pair.criado_em);
                  const materia = formatDiaCurto(pair.data_materia);
                  const expiraH = horasRestantes(pair.sugestao_expira_em);
                  return (
                    <article
                      key={pair.grupo_id}
                      className="grid gap-4 rounded-2xl border border-stone-200 bg-white p-5 md:grid-cols-[minmax(0,1fr)_auto]"
                    >
                      <div className="min-w-0 space-y-3">
                        <div className="flex flex-wrap items-center gap-2 text-xs text-stone-500">
                          <span
                            className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-bold ring-1 ${tipo.className}`}
                          >
                            {tipo.label}
                          </span>
                          <span>{pair.fonte || '—'}</span>
                          {pair.sentidos?.length ? (
                            <span className="font-semibold text-emerald-700">
                              · {pair.sentidos.join(', ')}
                            </span>
                          ) : null}
                        </div>
                        <p className="text-xs text-stone-500">
                          {sugerida ? <>Sugerida em {sugerida}</> : null}
                          {materia ? (
                            <>
                              {sugerida ? ' · ' : null}
                              Matéria de {materia}
                            </>
                          ) : null}
                          {expiraH != null ? (
                            <>
                              {(sugerida || materia) ? ' · ' : null}
                              expira em {expiraH} h
                            </>
                          ) : null}
                        </p>

                        <label className="block space-y-1">
                          <span className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-stone-500">
                            Título PT <Counter value={draft.titulo_pt} max={70} />
                          </span>
                          <input
                            className={field}
                            value={draft.titulo_pt}
                            maxLength={70}
                            onChange={(e) => updateDraft(pair.grupo_id, 'titulo_pt', e.target.value)}
                          />
                        </label>
                        <label className="block space-y-1">
                          <span className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-stone-500">
                            Resumo PT <Counter value={draft.resumo_pt} max={140} />
                          </span>
                          <input
                            className={field}
                            value={draft.resumo_pt}
                            maxLength={140}
                            onChange={(e) => updateDraft(pair.grupo_id, 'resumo_pt', e.target.value)}
                          />
                        </label>
                        <label className="block space-y-1">
                          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
                            Markdown PT
                          </span>
                          <textarea
                            className={`${field} min-h-[88px]`}
                            value={draft.markdown_pt}
                            onChange={(e) => updateDraft(pair.grupo_id, 'markdown_pt', e.target.value)}
                          />
                        </label>

                        <label className="block space-y-1">
                          <span className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-stone-500">
                            Título EN <Counter value={draft.titulo_en} max={70} />
                          </span>
                          <input
                            className={field}
                            value={draft.titulo_en}
                            maxLength={70}
                            onChange={(e) => updateDraft(pair.grupo_id, 'titulo_en', e.target.value)}
                          />
                        </label>
                        <label className="block space-y-1">
                          <span className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-stone-500">
                            Resumo EN <Counter value={draft.resumo_en} max={140} />
                          </span>
                          <input
                            className={field}
                            value={draft.resumo_en}
                            maxLength={140}
                            onChange={(e) => updateDraft(pair.grupo_id, 'resumo_en', e.target.value)}
                          />
                        </label>
                        <label className="block space-y-1">
                          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
                            Markdown EN
                          </span>
                          <textarea
                            className={`${field} min-h-[88px]`}
                            value={draft.markdown_en}
                            onChange={(e) => updateDraft(pair.grupo_id, 'markdown_en', e.target.value)}
                          />
                        </label>

                        {pair.link_url ? (
                          <a
                            href={pair.link_url}
                            target="_blank"
                            rel="noreferrer"
                            className="block break-all text-sm font-semibold text-emerald-700 hover:text-emerald-900"
                          >
                            {pair.link_url} ↗
                          </a>
                        ) : null}

                        {pair.trecho_base ? (
                          <blockquote className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
                            <span className="mb-1 block text-[11px] font-bold uppercase tracking-wider text-amber-800">
                              Trecho base
                            </span>
                            {pair.trecho_base}
                          </blockquote>
                        ) : null}
                      </div>

                      <div className="flex min-w-[150px] flex-col gap-2">
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void onPublish(pair)}
                          className="rounded-xl bg-emerald-500 px-3 py-2.5 text-sm font-bold text-white hover:bg-emerald-400 disabled:opacity-60"
                        >
                          {busy ? '…' : 'Publicar'}
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void onDiscard(pair)}
                          className="rounded-xl px-3 py-2.5 text-sm font-bold text-red-700 hover:bg-red-50 disabled:opacity-60"
                        >
                          Descartar
                        </button>
                      </div>
                    </article>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
