'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowLeft, Loader2, Sparkles } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import {
  discardCmsSugestao,
  fetchCmsSugestoes,
  generateCmsSugestoes,
  publishCmsSugestao,
  type CmsSugestaoPair,
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

function formatDate(value: string | null | undefined) {
  if (!value) return '—';
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!m) return value;
  return `${m[3]}/${m[2]}/${m[1]}`;
}

export function CmsSugestoes() {
  const { token } = useHubSession();
  const [rows, setRows] = useState<CmsSugestaoPair[]>([]);
  const [pending, setPending] = useState(0);
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  async function load() {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCmsSugestoes(token);
      setRows(data.sugestoes);
      setPending(data.pending_count);
      const next: Record<number, Draft> = {};
      for (const pair of data.sugestoes) next[pair.grupo_id] = draftFrom(pair);
      setDrafts(next);
    } catch {
      setError('Não foi possível carregar as sugestões.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

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
      const message =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { error?: string } } }).response?.data?.error
          : null;
      setError(message || 'Não foi possível publicar.');
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
    } catch {
      setError('Não foi possível descartar.');
    } finally {
      setBusyId(null);
    }
  }

  async function onGenerate() {
    if (!token) return;
    setGenerating(true);
    setError(null);
    setInfo(null);
    try {
      const result = await generateCmsSugestoes(token);
      setInfo(
        result.skipped === 'cap_atingido'
          ? 'Limite diário de 5 sugestões já atingido.'
          : `Geradas: ${result.created}.`
      );
      await load();
    } catch {
      setError('Não foi possível gerar agora.');
    } finally {
      setGenerating(false);
    }
  }

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
            Pendentes: {pending}.
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
      ) : rows.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-stone-300 bg-white px-5 py-8 text-sm text-stone-500">
          Nenhuma sugestão pendente. Use “Gerar sugestões”.
        </div>
      ) : (
        <div className="space-y-4">
          {rows.map((pair) => {
            const draft = drafts[pair.grupo_id] || draftFrom(pair);
            const tipo = TIPO_STYLE[pair.tipo || ''] || {
              label: pair.tipo || 'Item',
              className: 'bg-stone-100 text-stone-700 ring-stone-200',
            };
            const busy = busyId === pair.grupo_id;
            return (
              <article
                key={pair.grupo_id}
                className="grid gap-4 rounded-2xl border border-stone-200 bg-white p-5 md:grid-cols-[minmax(0,1fr)_auto]"
              >
                <div className="space-y-3 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-stone-500">
                    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-bold ring-1 ${tipo.className}`}>
                      {tipo.label}
                    </span>
                    <span>{pair.fonte || '—'}</span>
                    <span>· {formatDate(pair.data_materia)}</span>
                    {pair.sentidos?.length ? (
                      <span className="font-semibold text-emerald-700">
                        · {pair.sentidos.join(', ')}
                      </span>
                    ) : null}
                  </div>

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
                    <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Markdown PT</span>
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
                    <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Markdown EN</span>
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
      )}
    </div>
  );
}
