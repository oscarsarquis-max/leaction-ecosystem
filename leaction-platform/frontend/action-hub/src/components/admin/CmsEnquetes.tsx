'use client';

import Link from 'next/link';
import { FormEvent, useEffect, useState } from 'react';
import { ArrowLeft, BarChart3, Loader2, Save, Sparkles } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import {
  fetchCmsEnquetes,
  publicarCmsEnquete,
  saveCmsEnquete,
  sugerirCmsEnquete,
  type CmsEnquete,
  type CmsEnqueteBody,
} from '@/lib/admin-api';

type Opcao = {
  id: string;
  pt: string;
  en: string;
  detalhe_pt?: string;
  detalhe_en?: string;
  produto_id?: string;
  produto_nome?: string;
  produto_url?: string;
};

const field =
  'w-full rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm text-stone-900 outline-none ring-emerald-400 focus:ring-2';

function blankOpcoes(): Opcao[] {
  return [
    { id: 'a', pt: '', en: '' },
    { id: 'b', pt: '', en: '' },
  ];
}

function localInput(iso: string) {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toIso(local: string) {
  const date = new Date(local);
  return Number.isNaN(date.getTime()) ? '' : date.toISOString();
}

function apiErrorMessage(err: unknown, fallback: string) {
  if (err && typeof err === 'object' && 'response' in err) {
    const data = (err as { response?: { data?: { error?: string } } }).response?.data;
    if (data?.error) return data.error;
  }
  return fallback;
}

function statusLabel(status: string) {
  if (status === 'publicada') return 'Publicada';
  if (status === 'sugerida') return 'Sugerida';
  if (status === 'encerrada') return 'Encerrada';
  if (status === 'rascunho') return 'Rascunho';
  return status;
}

export function CmsEnquetes() {
  const { token } = useHubSession();
  const [rows, setRows] = useState<CmsEnquete[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [publishingId, setPublishingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const [perguntaPt, setPerguntaPt] = useState('');
  const [perguntaEn, setPerguntaEn] = useState('');
  const [opcoes, setOpcoes] = useState<Opcao[]>(blankOpcoes());
  const [abre, setAbre] = useState('');
  const [fecha, setFecha] = useState('');
  const [status, setStatus] = useState<'rascunho' | 'publicada' | 'sugerida'>('rascunho');

  async function load() {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      setRows(await fetchCmsEnquetes(token));
    } catch {
      setError('Não foi possível carregar as enquetes.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  function fill(row: CmsEnquete) {
    setEditing(row.id);
    setPerguntaPt(row.pergunta_pt);
    setPerguntaEn(row.pergunta_en);
    setOpcoes(
      row.opcoes.map((item) => ({
        id: item.id,
        pt: item.pt,
        en: item.en,
        detalhe_pt: item.detalhe_pt,
        detalhe_en: item.detalhe_en,
        produto_id: item.produto_id,
        produto_nome: item.produto_nome,
        produto_url: item.produto_url,
      }))
    );
    setAbre(localInput(row.abre_em));
    setFecha(localInput(row.fecha_em));
    setStatus(
      row.status === 'publicada'
        ? 'publicada'
        : row.status === 'sugerida'
          ? 'sugerida'
          : 'rascunho'
    );
    setError(null);
  }

  function reset() {
    setEditing(null);
    setPerguntaPt('');
    setPerguntaEn('');
    setOpcoes(blankOpcoes());
    setAbre('');
    setFecha('');
    setStatus('rascunho');
  }

  function updateOpcao(index: number, key: 'pt' | 'en' | 'detalhe_pt' | 'detalhe_en', value: string) {
    setOpcoes((current) =>
      current.map((item, i) => (i === index ? { ...item, [key]: value } : item))
    );
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    const filled = opcoes.filter((item) => item.pt.trim() && item.en.trim());
    if (filled.length < 2 || filled.length > 4) {
      setError('A enquete precisa de 2 a 4 opções, cada uma em PT e EN.');
      return;
    }
    const body: CmsEnqueteBody = {
      pergunta_pt: perguntaPt.trim(),
      pergunta_en: perguntaEn.trim(),
      opcoes: filled.map((item) => ({
        id: item.id,
        pt: item.pt.trim(),
        en: item.en.trim(),
        detalhe_pt: item.detalhe_pt?.trim() || undefined,
        detalhe_en: item.detalhe_en?.trim() || undefined,
        produto_id: item.produto_id,
        produto_nome: item.produto_nome,
        produto_url: item.produto_url,
      })),
      abre_em: toIso(abre),
      fecha_em: toIso(fecha),
      status,
    };
    if (!body.pergunta_pt || !body.pergunta_en || !body.abre_em || !body.fecha_em) {
      setError('Preencha a pergunta nos dois idiomas e as duas datas.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await saveCmsEnquete(token, body, editing ?? undefined);
      reset();
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível salvar a enquete.'));
    } finally {
      setSaving(false);
    }
  }

  async function onSugerir() {
    if (!token) return;
    setSuggesting(true);
    setError(null);
    try {
      await sugerirCmsEnquete(token);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível sugerir outra enquete.'));
    } finally {
      setSuggesting(false);
    }
  }

  async function onPublicar(id: number) {
    if (!token) return;
    setPublishingId(id);
    setError(null);
    try {
      await publicarCmsEnquete(token, id);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível publicar a enquete.'));
    } finally {
      setPublishingId(null);
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
            <BarChart3 className="size-5 text-emerald-500" aria-hidden />
            <h1 className="text-xl font-bold text-stone-900">Enquetes</h1>
          </div>
          <p className="max-w-xl text-sm text-stone-500">
            Enquete lúdica semanal. Produto e detalhe ficam só no admin até o voto.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/dashboard/cms/receitas"
            className="rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm font-semibold text-stone-700"
          >
            Receitas
          </Link>
          <button
            type="button"
            disabled={suggesting}
            onClick={() => void onSugerir()}
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-3 py-2 text-sm font-bold text-white disabled:opacity-60"
          >
            {suggesting ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
            Sugerir outra
          </button>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <form onSubmit={(event) => void onSubmit(event)} className="space-y-4 rounded-2xl border border-stone-200 bg-white p-5">
        <h2 className="text-sm font-bold uppercase tracking-wider text-stone-500">
          {editing ? `Editar enquete ${editing}` : 'Nova enquete'}
        </h2>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block space-y-1.5">
            <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Pergunta (PT)</span>
            <input className={field} value={perguntaPt} onChange={(e) => setPerguntaPt(e.target.value)} />
          </label>
          <label className="block space-y-1.5">
            <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Pergunta (EN)</span>
            <input className={field} value={perguntaEn} onChange={(e) => setPerguntaEn(e.target.value)} />
          </label>
          <label className="block space-y-1.5">
            <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Abre em</span>
            <input type="datetime-local" className={field} value={abre} onChange={(e) => setAbre(e.target.value)} />
          </label>
          <label className="block space-y-1.5">
            <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Fecha em</span>
            <input type="datetime-local" className={field} value={fecha} onChange={(e) => setFecha(e.target.value)} />
          </label>
        </div>
        <div className="space-y-3">
          {opcoes.map((opcao, index) => (
            <div key={opcao.id} className="space-y-2 rounded-xl border border-stone-100 bg-stone-50 p-3">
              <div className="grid gap-3 md:grid-cols-2">
                <label className="block space-y-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
                    Opção {index + 1} (PT)
                  </span>
                  <input className={field} value={opcao.pt} onChange={(e) => updateOpcao(index, 'pt', e.target.value)} />
                </label>
                <label className="block space-y-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
                    Opção {index + 1} (EN)
                  </span>
                  <input className={field} value={opcao.en} onChange={(e) => updateOpcao(index, 'en', e.target.value)} />
                </label>
                <label className="block space-y-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Detalhe PT</span>
                  <input
                    className={field}
                    value={opcao.detalhe_pt || ''}
                    onChange={(e) => updateOpcao(index, 'detalhe_pt', e.target.value)}
                  />
                </label>
                <label className="block space-y-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Detalhe EN</span>
                  <input
                    className={field}
                    value={opcao.detalhe_en || ''}
                    onChange={(e) => updateOpcao(index, 'detalhe_en', e.target.value)}
                  />
                </label>
              </div>
              {opcao.produto_nome ? (
                <p className="text-xs text-stone-500">
                  Produto (admin): {opcao.produto_nome}
                  {opcao.produto_url ? (
                    <>
                      {' '}
                      ·{' '}
                      <a className="underline" href={opcao.produto_url} target="_blank" rel="noreferrer">
                        link
                      </a>
                    </>
                  ) : null}
                </p>
              ) : null}
            </div>
          ))}
          <div className="flex gap-2">
            {opcoes.length < 4 ? (
              <button
                type="button"
                className="rounded-xl border border-stone-300 px-3 py-2 text-sm font-semibold text-stone-700"
                onClick={() =>
                  setOpcoes((current) => [
                    ...current,
                    { id: String.fromCharCode(97 + current.length), pt: '', en: '' },
                  ])
                }
              >
                Adicionar opção
              </button>
            ) : null}
            {opcoes.length > 2 ? (
              <button
                type="button"
                className="rounded-xl border border-stone-300 px-3 py-2 text-sm font-semibold text-stone-700"
                onClick={() => setOpcoes((current) => current.slice(0, -1))}
              >
                Remover opção
              </button>
            ) : null}
          </div>
        </div>
        <label className="block max-w-xs space-y-1.5">
          <span className="text-xs font-bold uppercase tracking-wider text-stone-500">Publicação</span>
          <select
            className={field}
            value={status}
            onChange={(e) => setStatus(e.target.value as 'rascunho' | 'publicada' | 'sugerida')}
          >
            <option value="rascunho">Rascunho</option>
            <option value="sugerida">Sugerida</option>
            <option value="publicada">Publicada</option>
          </select>
        </label>
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-bold text-white disabled:opacity-60"
          >
            {saving ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
            {status === 'publicada' ? 'Publicar' : 'Salvar'}
          </button>
          {editing ? (
            <button type="button" className="rounded-xl border border-stone-300 px-4 py-2.5 text-sm font-semibold" onClick={reset}>
              Cancelar
            </button>
          ) : null}
        </div>
      </form>

      {loading ? (
        <p className="text-sm text-stone-500">Carregando…</p>
      ) : (
        <ul className="space-y-3">
          {rows.map((row) => (
            <li key={row.id} className="rounded-2xl border border-stone-200 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-bold text-stone-900">{row.pergunta_pt}</p>
                  <p className="text-sm text-stone-500">{row.pergunta_en}</p>
                  <p className="mt-1 text-xs uppercase tracking-wider text-stone-400">
                    {statusLabel(row.status)} · {row.total ?? 0} votos
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {row.status === 'sugerida' || row.status === 'rascunho' ? (
                    <button
                      type="button"
                      disabled={publishingId === row.id}
                      className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-3 py-2 text-sm font-bold text-white disabled:opacity-60"
                      onClick={() => void onPublicar(row.id)}
                    >
                      {publishingId === row.id ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : null}
                      Publicar enquete
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="rounded-xl border border-stone-300 px-3 py-2 text-sm font-semibold"
                    onClick={() => fill(row)}
                  >
                    Editar
                  </button>
                </div>
              </div>
              <ul className="mt-3 space-y-2 text-sm text-stone-700">
                {row.opcoes.map((opcao) => {
                  const pct = row.resultado?.find((item) => item.id === opcao.id)?.pct ?? 0;
                  return (
                    <li key={opcao.id} className="rounded-lg bg-stone-50 px-3 py-2">
                      <p>
                        {opcao.pt} / {opcao.en} — {pct}%
                      </p>
                      {(opcao.detalhe_pt || opcao.detalhe_en) && (
                        <p className="text-xs text-stone-500">
                          Detalhe: {opcao.detalhe_pt || '—'} / {opcao.detalhe_en || '—'}
                        </p>
                      )}
                      {opcao.produto_nome ? (
                        <p className="text-xs text-stone-500">
                          Produto (admin): {opcao.produto_nome}
                          {opcao.produto_url ? (
                            <>
                              {' '}
                              ·{' '}
                              <a className="underline" href={opcao.produto_url} target="_blank" rel="noreferrer">
                                loja
                              </a>
                            </>
                          ) : null}
                        </p>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </li>
          ))}
          {rows.length === 0 ? <li className="text-sm text-stone-500">Nenhuma enquete ainda.</li> : null}
        </ul>
      )}
    </div>
  );
}
