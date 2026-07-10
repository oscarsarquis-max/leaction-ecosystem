import { useEffect, useState } from 'react';
import { fetchKaizenTicket } from '../../services/kaizenApi';
import { parseOccurrenceFromTicket } from '../../utils/kaizenTicketMeta';

const WHY_KEYS = ['why_1', 'why_2', 'why_3', 'why_4', 'why_5'];

export default function KaizenOriginModal({ ticketId, onClose }) {
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!ticketId) return undefined;
    let cancelled = false;
    setLoading(true);
    setError('');
    fetchKaizenTicket(ticketId)
      .then((response) => {
        if (!cancelled) setTicket(response.ticket || response);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'Não foi possível carregar o ticket de origem.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ticketId]);

  if (!ticketId) return null;

  const occurrence = ticket ? parseOccurrenceFromTicket(ticket) : null;
  const rca = ticket?.root_cause_analysis || {};

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-orange-700">
              Origem no Gemba
            </p>
            <h2 className="mt-1 text-lg font-bold text-slate-900">
              {ticket?.title || 'Ticket Kaizen'}
            </h2>
          </div>
          <button
            type="button"
            className="rounded-lg border border-slate-200 px-2 py-1 text-sm text-slate-600 hover:bg-slate-50"
            onClick={onClose}
          >
            Fechar
          </button>
        </div>

        {loading && <p className="mt-6 text-sm text-slate-500">Carregando origem…</p>}
        {error && (
          <p className="mt-6 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        {!loading && ticket && (
          <div className="mt-6 space-y-4 text-sm">
            <section className="rounded-xl border border-orange-100 bg-orange-50/60 p-4">
              <h3 className="text-xs font-bold uppercase tracking-wide text-orange-800">
                Ocorrência original
              </h3>
              <dl className="mt-3 space-y-2">
                <div>
                  <dt className="font-semibold text-slate-700">Onde</dt>
                  <dd className="text-slate-600">{occurrence?.location}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-slate-700">O que aconteceu</dt>
                  <dd className="text-slate-600">{occurrence?.whatHappened}</dd>
                </div>
                {occurrence?.immediateAction && (
                  <div>
                    <dt className="font-semibold text-slate-700">Ação imediata</dt>
                    <dd className="text-slate-600">{occurrence.immediateAction}</dd>
                  </div>
                )}
              </dl>
            </section>

            {ticket.temporary_containment_action && (
              <section className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                <h3 className="text-xs font-bold uppercase tracking-wide text-amber-900">
                  Contenção adotada
                </h3>
                <p className="mt-2 text-slate-700">{ticket.temporary_containment_action}</p>
              </section>
            )}

            <section className="rounded-xl border border-sky-100 bg-sky-50/50 p-4">
              <h3 className="text-xs font-bold uppercase tracking-wide text-sky-800">
                5 Porquês
              </h3>
              <dl className="mt-3 space-y-2">
                {WHY_KEYS.map((key, index) =>
                  rca[key] ? (
                    <div key={key}>
                      <dt className="font-semibold text-slate-700">Por que {index + 1}</dt>
                      <dd className="text-slate-600">{rca[key]}</dd>
                    </div>
                  ) : null,
                )}
                {rca.root_cause && (
                  <div>
                    <dt className="font-semibold text-violet-800">Causa raiz</dt>
                    <dd className="text-slate-700">{rca.root_cause}</dd>
                  </div>
                )}
              </dl>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
