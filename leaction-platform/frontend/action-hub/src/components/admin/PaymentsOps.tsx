'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CheckCircle2,
  Clock3,
  Loader2,
  MessageSquarePlus,
  RefreshCw,
} from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import {
  fetchAdminPaymentStats,
  fetchAdminPayments,
  formatBrl,
  postAdminPaymentNotice,
  type AdminPayment,
  type AdminPaymentCounts,
  type AdminPaymentStatPoint,
} from '@/lib/admin-api';

const STATUS_FILTERS = [
  { id: '', label: 'Todos' },
  { id: 'PENDING', label: 'Pendentes' },
  { id: 'PAID', label: 'Aprovados' },
] as const;

function formatDate(raw: string | null | undefined) {
  const text = String(raw || '').trim();
  if (!text) return '—';
  const hasTz = /([zZ]|[+-]\d{2}:?\d{2})$/.test(text);
  const normalized = hasTz
    ? text
    : /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}/.test(text)
      ? `${text.replace(' ', 'T')}Z`
      : text;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return text;
  return new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/Sao_Paulo',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function StatusBadge({ status }: { status: string }) {
  const s = String(status || '').toUpperCase();
  if (s === 'PAID') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-800">
        <CheckCircle2 className="size-3.5" />
        Aprovado
      </span>
    );
  }
  if (s === 'PENDING') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">
        <Clock3 className="size-3.5" />
        Pendente
      </span>
    );
  }
  return (
    <span className="inline-flex rounded-full bg-stone-200 px-2.5 py-1 text-xs font-semibold text-stone-700">
      {status || '—'}
    </span>
  );
}

export function PaymentsOps() {
  const { token } = useHubSession();
  const [statusFilter, setStatusFilter] = useState('');
  const [appFilter, setAppFilter] = useState('');
  const [payments, setPayments] = useState<AdminPayment[]>([]);
  const [counts, setCounts] = useState<AdminPaymentCounts>({
    total: 0,
    pending: 0,
    paid: 0,
    other: 0,
  });
  const [stats, setStats] = useState<AdminPaymentStatPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [noticeOrderId, setNoticeOrderId] = useState<string | null>(null);
  const [noticeText, setNoticeText] = useState('');
  const [noticeSending, setNoticeSending] = useState(false);
  const [noticeFeedback, setNoticeFeedback] = useState('');

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const [list, series] = await Promise.all([
        fetchAdminPayments(token, {
          status: statusFilter || undefined,
          app_id: appFilter || undefined,
          limit: 100,
        }),
        fetchAdminPaymentStats(token, {
          days: 30,
          app_id: appFilter || undefined,
        }),
      ]);
      setPayments(list.payments);
      setCounts(list.counts);
      setStats(series);
    } catch (err) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? String(
              (err as { response?: { data?: { error?: string } } }).response?.data
                ?.error || ''
            )
          : '';
      setError(msg || 'Falha ao carregar pagamentos');
    } finally {
      setLoading(false);
    }
  }, [token, statusFilter, appFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  // Polling leve para acompanhar em tempo quase real
  useEffect(() => {
    if (!token) return undefined;
    const id = window.setInterval(() => {
      void load();
    }, 8_000);
    return () => window.clearInterval(id);
  }, [token, load]);

  const planSummary = useMemo(() => {
    const map = new Map<
      string,
      { plan: string; app: string; paid: number; pending: number; revenue: number }
    >();
    for (const row of stats) {
      const key = `${row.app_id}::${row.plan_name}`;
      const prev = map.get(key) || {
        plan: row.plan_name,
        app: row.app_id,
        paid: 0,
        pending: 0,
        revenue: 0,
      };
      prev.paid += row.orders_paid;
      prev.pending += row.orders_pending;
      prev.revenue += row.revenue;
      map.set(key, prev);
    }
    return Array.from(map.values()).sort((a, b) => b.revenue - a.revenue);
  }, [stats]);

  async function sendNotice(orderId: string) {
    if (!token || !noticeText.trim()) return;
    setNoticeSending(true);
    setNoticeFeedback('');
    try {
      await postAdminPaymentNotice(token, orderId, {
        message: noticeText.trim(),
        status_label: 'pending_review',
      });
      setNoticeFeedback('Aviso enviado à aplicação.');
      setNoticeText('');
      setNoticeOrderId(null);
      await load();
    } catch (err) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? String(
              (err as { response?: { data?: { error?: string } } }).response?.data
                ?.error || ''
            )
          : '';
      setNoticeFeedback(msg || 'Falha ao enviar aviso');
    } finally {
      setNoticeSending(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-stone-900">Pagamentos &amp; Ops</h1>
          <p className="mt-1 text-sm text-stone-500">
            Acompanhe status em tempo quase real, evolução por plano e intervenha com
            avisos nas apps satélite.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="inline-flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-3 py-2 text-xs font-semibold text-stone-700 hover:bg-stone-50"
        >
          <RefreshCw className={`size-3.5 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-4">
        {[
          { label: 'Total', value: counts.total, tone: 'bg-stone-100 text-stone-800' },
          { label: 'Pendentes', value: counts.pending, tone: 'bg-amber-50 text-amber-900' },
          { label: 'Aprovados', value: counts.paid, tone: 'bg-emerald-50 text-emerald-900' },
          { label: 'Outros', value: counts.other, tone: 'bg-slate-50 text-slate-800' },
        ].map((card) => (
          <div
            key={card.label}
            className={`rounded-2xl px-4 py-3 ${card.tone} ring-1 ring-black/5`}
          >
            <p className="text-[11px] font-semibold uppercase tracking-wide opacity-70">
              {card.label}
            </p>
            <p className="mt-1 text-2xl font-black tabular-nums">{card.value}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.id || 'all'}
            type="button"
            onClick={() => setStatusFilter(f.id)}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
              statusFilter === f.id
                ? 'bg-orange-600 text-white'
                : 'bg-stone-100 text-stone-700 hover:bg-stone-200'
            }`}
          >
            {f.label}
          </button>
        ))}
        <select
          value={appFilter}
          onChange={(e) => setAppFilter(e.target.value)}
          className="ml-auto rounded-xl border border-stone-200 bg-white px-3 py-1.5 text-xs font-semibold text-stone-700"
        >
          <option value="">Todas as apps</option>
          <option value="inove4us">inove4us</option>
          <option value="paneldx">paneldx</option>
        </select>
      </div>

      <section className="rounded-2xl border border-stone-200 bg-stone-50/60 p-4">
        <h2 className="text-sm font-bold text-stone-900">Evolução por plano (30 dias)</h2>
        {planSummary.length === 0 ? (
          <p className="mt-2 text-sm text-stone-500">Sem dados no período.</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wide text-stone-500">
                  <th className="px-2 py-2">App</th>
                  <th className="px-2 py-2">Plano</th>
                  <th className="px-2 py-2">Aprovados</th>
                  <th className="px-2 py-2">Pendentes</th>
                  <th className="px-2 py-2">Receita</th>
                </tr>
              </thead>
              <tbody>
                {planSummary.map((row) => (
                  <tr key={`${row.app}-${row.plan}`} className="border-t border-stone-200">
                    <td className="px-2 py-2 font-medium text-stone-700">{row.app}</td>
                    <td className="px-2 py-2 text-stone-800">{row.plan}</td>
                    <td className="px-2 py-2 tabular-nums text-emerald-800">{row.paid}</td>
                    <td className="px-2 py-2 tabular-nums text-amber-800">{row.pending}</td>
                    <td className="px-2 py-2 tabular-nums font-semibold text-stone-900">
                      {formatBrl(row.revenue)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <section className="overflow-x-auto rounded-2xl border border-stone-200">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-stone-50 text-xs uppercase tracking-wide text-stone-500">
            <tr>
              <th className="px-3 py-2.5">Quando</th>
              <th className="px-3 py-2.5">Cliente</th>
              <th className="px-3 py-2.5">Plano / App</th>
              <th className="px-3 py-2.5">Valor</th>
              <th className="px-3 py-2.5">Status</th>
              <th className="px-3 py-2.5">Ação</th>
            </tr>
          </thead>
          <tbody>
            {loading && payments.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-stone-500">
                  <Loader2 className="mx-auto size-5 animate-spin" />
                </td>
              </tr>
            ) : null}
            {!loading && payments.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-stone-500">
                  Nenhum pagamento encontrado.
                </td>
              </tr>
            ) : null}
            {payments.map((p) => (
              <tr key={p.id} className="border-t border-stone-100 align-top">
                <td className="px-3 py-3 text-stone-600">{formatDate(p.created_at)}</td>
                <td className="px-3 py-3">
                  <p className="font-medium text-stone-800">{p.subject_id || p.payer_email}</p>
                  <p className="font-mono text-[10px] text-stone-400">{p.id.slice(0, 8)}…</p>
                </td>
                <td className="px-3 py-3">
                  <p className="font-semibold text-stone-900">{p.plan_name || p.product_name}</p>
                  <p className="text-xs text-stone-500">
                    {p.app_id || '—'} · {p.plan_sku || p.product_sku || '—'}
                  </p>
                  {p.latest_notice ? (
                    <p className="mt-1 text-xs text-orange-800">Último aviso: {p.latest_notice}</p>
                  ) : null}
                </td>
                <td className="px-3 py-3 tabular-nums font-semibold text-stone-900">
                  {p.amount != null ? formatBrl(p.amount, p.currency) : '—'}
                </td>
                <td className="px-3 py-3">
                  <StatusBadge status={p.status} />
                </td>
                <td className="px-3 py-3">
                  {String(p.status).toUpperCase() === 'PENDING' || p.app_id === 'inove4us' ? (
                    <button
                      type="button"
                      onClick={() => {
                        setNoticeOrderId(p.id);
                        setNoticeText(
                          String(p.status).toUpperCase() === 'PENDING'
                            ? 'Seu pagamento está em análise no Mercado Pago. Avisaremos assim que for confirmado.'
                            : ''
                        );
                        setNoticeFeedback('');
                      }}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-orange-50 px-2.5 py-1.5 text-xs font-semibold text-orange-900 ring-1 ring-orange-200 hover:bg-orange-100"
                    >
                      <MessageSquarePlus className="size-3.5" />
                      Avisar app
                    </button>
                  ) : (
                    <span className="text-xs text-stone-400">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {noticeOrderId ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl">
            <h3 className="text-base font-bold text-stone-900">Mensagem para a app</h3>
            <p className="mt-1 text-xs text-stone-500">
              Será entregue via webhook (ex.: banner no inove4us).
            </p>
            <textarea
              className="mt-3 w-full rounded-xl border border-stone-200 px-3 py-2 text-sm text-stone-800 outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20"
              rows={4}
              value={noticeText}
              onChange={(e) => setNoticeText(e.target.value)}
              placeholder="Mensagem visível ao usuário…"
            />
            {noticeFeedback ? (
              <p className="mt-2 text-xs text-stone-600">{noticeFeedback}</p>
            ) : null}
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setNoticeOrderId(null)}
                className="rounded-xl px-3 py-2 text-xs font-semibold text-stone-600 hover:bg-stone-100"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={noticeSending || noticeText.trim().length < 3}
                onClick={() => void sendNotice(noticeOrderId)}
                className="inline-flex items-center gap-2 rounded-xl bg-orange-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-60"
              >
                {noticeSending ? <Loader2 className="size-3.5 animate-spin" /> : null}
                Enviar aviso
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
