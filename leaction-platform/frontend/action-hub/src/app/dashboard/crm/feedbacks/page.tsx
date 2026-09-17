'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Loader2, Lock } from 'lucide-react';
import { useAuthGate } from '@/lib/require-hub-login';

type Feedback = {
  id: number;
  user_email: string | null;
  id_clie: number | null;
  tipo: string;
  mensagem: string;
  status: string;
  created_at: string | null;
  retorno_texto?: string | null;
  retorno_em?: string | null;
};

type ListaResponse = {
  ok?: boolean;
  error?: string;
  feedbacks?: Feedback[];
};

const STATUS_OPTS = [
  { value: '', label: 'Todos (pendente primeiro)' },
  { value: 'pendente', label: 'Pendente' },
  { value: 'lido', label: 'Lido' },
  { value: 'recompensado', label: 'Entrou no roteiro' },
  { value: 'arquivado', label: 'Arquivado' },
] as const;

const TIPO_LABEL: Record<string, string> = {
  bug: 'Bug',
  ideia: 'Ideia',
  melhoria: 'Melhoria',
};

function formatData(iso: string | null) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
}

export default function CrmFeedbacksPage() {
  const { hydrated, isAuthenticated, requireLogin } = useAuthGate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [items, setItems] = useState<Feedback[]>([]);
  const [statusFiltro, setStatusFiltro] = useState('pendente');
  const [savingId, setSavingId] = useState<number | null>(null);
  const [avisoManual, setAvisoManual] = useState('');
  const [drafts, setDrafts] = useState<Record<number, { status: string; retorno: string }>>({});

  useEffect(() => {
    if (!hydrated) return;
    if (!isAuthenticated) {
      requireLogin('/dashboard/crm/feedbacks', 'Faça login para revisar os feedbacks da Nina.');
    }
  }, [hydrated, isAuthenticated, requireLogin]);

  const load = useCallback(async () => {
    const qs = new URLSearchParams();
    if (statusFiltro) qs.set('status', statusFiltro);
    const res = await fetch(`/api/crm/feedbacks${qs.toString() ? `?${qs}` : ''}`, {
      cache: 'no-store',
    });
    const json = (await res.json()) as ListaResponse;
    if (!res.ok || json.ok === false) {
      throw new Error(json.error || `HTTP ${res.status}`);
    }
    return json.feedbacks || [];
  }, [statusFiltro]);

  useEffect(() => {
    if (!hydrated || !isAuthenticated) return;
    let cancelled = false;
    setLoading(true);
    setError('');
    load()
      .then((rows) => {
        if (cancelled) return;
        setItems(rows);
        setDrafts((prev) => {
          const next = { ...prev };
          for (const r of rows) {
            if (!next[r.id]) {
              next[r.id] = { status: r.status, retorno: '' };
            }
          }
          return next;
        });
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Falha ao carregar');
          setItems([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [hydrated, isAuthenticated, load]);

  const pendentes = useMemo(
    () => items.filter((f) => f.status === 'pendente').length,
    [items]
  );

  async function salvar(f: Feedback) {
    const draft = drafts[f.id] || { status: f.status, retorno: '' };
    const payload: { status?: string; retorno_texto?: string } = {};
    if (draft.status && draft.status !== f.status) payload.status = draft.status;
    const retorno = (draft.retorno || '').trim();
    if (retorno) payload.retorno_texto = retorno;
    if (!payload.status && !payload.retorno_texto) {
      if (draft.status === f.status) {
        payload.status = draft.status;
      }
    }
    setSavingId(f.id);
    setError('');
    try {
      const res = await fetch(`/api/crm/feedbacks/${f.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const json = (await res.json()) as {
        ok?: boolean;
        error?: string;
        feedback?: Feedback;
        aviso_concessao_manual?: boolean;
      };
      if (!res.ok || json.ok === false) {
        throw new Error(json.error || `HTTP ${res.status}`);
      }
      if (payload.status === 'recompensado') {
        setAvisoManual(
          'Marque a concessão dos 10 planejamentos Premium manualmente no Inove/crédito institucional — isso aqui só registra que foi aprovado, não credita nada.'
        );
      }
      setDrafts((prev) => ({
        ...prev,
        [f.id]: { status: json.feedback?.status || draft.status, retorno: '' },
      }));
      const rows = await load();
      setItems(rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao salvar');
    } finally {
      setSavingId(null);
    }
  }

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
          href="/dashboard/crm/pos-venda"
          className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-emerald-800"
        >
          <ArrowLeft className="size-4" aria-hidden />
          Pós-venda
        </Link>
        <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-stone-900">Feedbacks da Nina</h1>
            <p className="mt-1 text-sm text-stone-500">
              Fila de revisão do Programa de Co-criação. Sem crédito automático.
            </p>
          </div>
          <p className="text-sm text-stone-500">
            {pendentes} pendente{pendentes === 1 ? '' : 's'} nesta lista
          </p>
        </header>

        {avisoManual ? (
          <div
            role="status"
            className="mb-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          >
            {avisoManual}
          </div>
        ) : null}

        <div className="mb-4">
          <label className="text-xs font-semibold uppercase tracking-wide text-stone-500">
            Status
            <select
              className="ml-2 rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-sm font-medium text-stone-800"
              value={statusFiltro}
              onChange={(e) => setStatusFiltro(e.target.value)}
            >
              {STATUS_OPTS.map((o) => (
                <option key={o.value || 'all'} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error ? (
          <p className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
            {error}
          </p>
        ) : null}

        {loading ? (
          <div className="flex items-center gap-2 text-stone-500">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            Carregando…
          </div>
        ) : items.length === 0 ? (
          <p className="rounded-xl border border-dashed border-stone-200 bg-white px-4 py-8 text-center text-sm text-stone-500">
            Nenhum feedback neste filtro.
          </p>
        ) : (
          <ul className="space-y-3">
            {items.map((f) => {
              const draft = drafts[f.id] || { status: f.status, retorno: '' };
              return (
                <li
                  key={f.id}
                  className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-800">
                        {TIPO_LABEL[f.tipo] || f.tipo}
                      </span>
                      <span className="rounded-full bg-stone-100 px-2.5 py-0.5 text-xs font-medium text-stone-600">
                        {f.status}
                      </span>
                      <span className="text-xs text-stone-400">{formatData(f.created_at)}</span>
                    </div>
                    <p className="text-xs text-stone-500">
                      {f.user_email || '—'} · id_clie {f.id_clie ?? '—'}
                    </p>
                  </div>
                  <p className="mt-3 whitespace-pre-wrap text-sm text-stone-800">{f.mensagem}</p>
                  {f.retorno_texto ? (
                    <p className="mt-2 rounded-lg bg-violet-50 px-3 py-2 text-xs text-violet-900">
                      Último retorno: {f.retorno_texto}
                    </p>
                  ) : null}
                  <div className="mt-4 grid gap-3 md:grid-cols-[12rem_1fr_auto]">
                    <label className="text-xs font-semibold text-stone-500">
                      Status
                      <select
                        className="mt-1 w-full rounded-lg border border-stone-200 px-2 py-1.5 text-sm font-medium text-stone-800"
                        value={draft.status}
                        onChange={(e) =>
                          setDrafts((prev) => ({
                            ...prev,
                            [f.id]: { ...draft, status: e.target.value },
                          }))
                        }
                        disabled={savingId === f.id}
                      >
                        <option value="pendente">pendente</option>
                        <option value="lido">lido</option>
                        <option value="recompensado">recompensado (entrou no roteiro)</option>
                        <option value="arquivado">arquivado</option>
                      </select>
                    </label>
                    <label className="text-xs font-semibold text-stone-500">
                      Retorno pra quem enviou (opcional)
                      <textarea
                        className="mt-1 w-full rounded-lg border border-stone-200 px-2 py-1.5 text-sm text-stone-800"
                        rows={2}
                        value={draft.retorno}
                        placeholder="Aparece como card lilás na Mesa do professor"
                        onChange={(e) =>
                          setDrafts((prev) => ({
                            ...prev,
                            [f.id]: { ...draft, retorno: e.target.value },
                          }))
                        }
                        disabled={savingId === f.id}
                      />
                    </label>
                    <button
                      type="button"
                      className="self-end rounded-xl bg-emerald-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                      onClick={() => void salvar(f)}
                      disabled={savingId === f.id}
                    >
                      {savingId === f.id ? 'Salvando…' : 'Salvar'}
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
