'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import {
  ArrowLeft,
  Check,
  Loader2,
  MessageCircle,
  NotebookPen,
  X,
} from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import {
  fetchCmsReceitaWhatsapp,
  fetchCmsReceitas,
  publicarCmsReceita,
  recusarCmsReceita,
  type CmsReceita,
} from '@/lib/admin-api';

function apiErrorMessage(err: unknown, fallback: string) {
  if (err && typeof err === 'object' && 'response' in err) {
    const data = (err as { response?: { data?: { error?: string } } }).response?.data;
    if (data?.error) return data.error;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

function statusLabel(status: string) {
  if (status === 'recebida') return 'Recebida';
  if (status === 'publicada') return 'Publicada';
  if (status === 'recusada') return 'Recusada';
  return status;
}

function correcoesTexto(revisao: CmsReceita['revisao']): string[] {
  if (!revisao?.correcoes_pt) return [];
  if (Array.isArray(revisao.correcoes_pt)) {
    return revisao.correcoes_pt.map(String).filter(Boolean);
  }
  return Object.entries(revisao.correcoes_pt)
    .filter(([, v]) => Boolean(v))
    .map(([k, v]) => `${k}: ${v}`);
}

export function CmsReceitas() {
  const { token } = useHubSession();
  const [rows, setRows] = useState<CmsReceita[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      setRows(await fetchCmsReceitas(token));
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível carregar as receitas.'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function onPublicar(id: number) {
    if (!token) return;
    setBusyId(id);
    setError(null);
    try {
      await publicarCmsReceita(token, id);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível publicar.'));
    } finally {
      setBusyId(null);
    }
  }

  async function onRecusar(id: number) {
    if (!token) return;
    setBusyId(id);
    setError(null);
    try {
      await recusarCmsReceita(token, id);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível recusar.'));
    } finally {
      setBusyId(null);
    }
  }

  async function onWhatsapp(id: number, tipo: 'ajuste' | 'publicou') {
    if (!token) return;
    setBusyId(id);
    setError(null);
    try {
      const url = await fetchCmsReceitaWhatsapp(token, id, tipo);
      window.open(url, '_blank', 'noopener,noreferrer');
    } catch (err) {
      setError(apiErrorMessage(err, 'Não foi possível abrir o WhatsApp.'));
    } finally {
      setBusyId(null);
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
            <NotebookPen className="size-5 text-emerald-500" aria-hidden />
            <h1 className="text-xl font-bold text-stone-900">Receitas</h1>
          </div>
          <p className="max-w-xl text-sm text-stone-500">
            Envios dos leitores com revisão da IA. Publique, peça ajuste ou recuse.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/dashboard/cms/enquetes"
            className="rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm font-semibold text-stone-700"
          >
            Enquetes
          </Link>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {loading ? (
        <p className="text-sm text-stone-500">Carregando…</p>
      ) : (
        <ul className="space-y-4">
          {rows.map((row) => {
            const busy = busyId === row.id;
            const en = row.revisao?.en;
            const correcoes = correcoesTexto(row.revisao);
            return (
              <li key={row.id} className="rounded-2xl border border-stone-200 bg-white p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wider text-stone-400">
                      {statusLabel(row.status)}
                      {row.cliente_loja ? ' · cliente da loja' : ''}
                      {row.telefone_mascarado ? ` · ${row.telefone_mascarado}` : ''}
                    </p>
                    <h2 className="mt-1 text-lg font-bold text-stone-900">{row.titulo}</h2>
                    <p className="text-sm text-stone-500">
                      {row.nome}
                      {row.cidade ? ` · ${row.cidade}` : ''}
                      {row.instagram ? ` · @${row.instagram}` : ''}
                    </p>
                  </div>
                  {row.foto_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={row.foto_url}
                      alt=""
                      className="h-20 w-20 rounded-xl object-cover"
                    />
                  ) : null}
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div className="space-y-2 text-sm text-stone-700">
                    <p className="text-xs font-bold uppercase tracking-wider text-stone-400">
                      Original (PT)
                    </p>
                    <p className="whitespace-pre-wrap">{row.historia}</p>
                    <p className="whitespace-pre-wrap text-stone-500">
                      <span className="font-semibold text-stone-700">Ingredientes:</span>{' '}
                      {row.ingredientes}
                    </p>
                    <p className="whitespace-pre-wrap text-stone-500">
                      <span className="font-semibold text-stone-700">Preparo:</span> {row.preparo}
                    </p>
                  </div>
                  <div className="space-y-2 text-sm text-stone-700">
                    <p className="text-xs font-bold uppercase tracking-wider text-stone-400">
                      Revisão IA + EN
                    </p>
                    {row.revisao?.alerta_dado_pessoal ? (
                      <p className="rounded-lg bg-amber-50 px-3 py-2 text-amber-800">
                        Alerta de dado pessoal
                        {row.revisao.alerta_motivo ? `: ${row.revisao.alerta_motivo}` : ''}
                      </p>
                    ) : null}
                    {correcoes.length ? (
                      <ul className="list-disc space-y-1 pl-5 text-stone-600">
                        {correcoes.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-stone-400">Sem correções listadas.</p>
                    )}
                    {en ? (
                      <div className="rounded-xl border border-stone-100 bg-stone-50 p-3">
                        <p className="font-semibold">{en.titulo || '—'}</p>
                        <p className="mt-1 whitespace-pre-wrap text-stone-600">
                          {en.historia || '—'}
                        </p>
                        {en.ingredientes ? (
                          <p className="mt-2 whitespace-pre-wrap text-stone-500">
                            {en.ingredientes}
                          </p>
                        ) : null}
                        {en.preparo ? (
                          <p className="mt-2 whitespace-pre-wrap text-stone-500">{en.preparo}</p>
                        ) : null}
                      </div>
                    ) : (
                      <p className="text-stone-400">Tradução EN indisponível.</p>
                    )}
                  </div>
                </div>

                {row.status === 'recebida' ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void onPublicar(row.id)}
                      className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-3 py-2 text-sm font-bold text-white disabled:opacity-60"
                    >
                      {busy ? <Loader2 className="size-4 animate-spin" /> : <Check className="size-4" />}
                      Publicar
                    </button>
                    <button
                      type="button"
                      disabled={busy || !row.tem_telefone}
                      onClick={() => void onWhatsapp(row.id, 'ajuste')}
                      className="inline-flex items-center gap-2 rounded-xl border border-stone-300 px-3 py-2 text-sm font-semibold text-stone-700 disabled:opacity-60"
                    >
                      <MessageCircle className="size-4" />
                      Pedir ajuste WhatsApp
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void onRecusar(row.id)}
                      className="inline-flex items-center gap-2 rounded-xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 disabled:opacity-60"
                    >
                      <X className="size-4" />
                      Recusar
                    </button>
                  </div>
                ) : null}

                {row.status === 'publicada' ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={busy || !row.tem_telefone}
                      onClick={() => void onWhatsapp(row.id, 'publicou')}
                      className="inline-flex items-center gap-2 rounded-xl border border-stone-300 px-3 py-2 text-sm font-semibold text-stone-700 disabled:opacity-60"
                    >
                      <MessageCircle className="size-4" />
                      Avisar que publicou
                    </button>
                  </div>
                ) : null}
              </li>
            );
          })}
          {rows.length === 0 ? (
            <li className="text-sm text-stone-500">Nenhuma receita enviada ainda.</li>
          ) : null}
        </ul>
      )}
    </div>
  );
}
