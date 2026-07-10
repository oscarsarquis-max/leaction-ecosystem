import { useState } from 'react';
import { TD_OFFICIAL_DOMAINS } from '../../constants/td';
import { escalateKaizenTicket } from '../../services/kaizenApi';

export default function KaizenEscalatePanel({
  ticketId,
  rootCauseAnalysis,
  disabled = false,
  onSuccess,
  onError,
}) {
  const [open, setOpen] = useState(false);
  const [domain, setDomain] = useState(TD_OFFICIAL_DOMAINS[2]);
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState('');

  async function handleEscalate(event) {
    event.preventDefault();
    if (!ticketId || !domain) return;

    setSubmitting(true);
    setLocalError('');
    try {
      const payload = { paneldx_domain: domain };
      if (rootCauseAnalysis) {
        payload.root_cause_analysis = rootCauseAnalysis;
      }
      const response = await escalateKaizenTicket(ticketId, payload);
      onSuccess?.(response);
      setOpen(false);
    } catch (err) {
      const message = err.message || 'Não foi possível escalar o problema.';
      setLocalError(message);
      onError?.(message);
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen(true)}
        className="w-full rounded-xl border border-violet-300 bg-violet-50 px-4 py-2.5 text-sm font-semibold text-violet-900 transition hover:bg-violet-100 disabled:opacity-60"
      >
        Escalar para Sprint Organizacional
      </button>
    );
  }

  return (
    <form
      onSubmit={handleEscalate}
      className="rounded-xl border border-violet-200 bg-violet-50/70 p-4 space-y-3"
    >
      <div>
        <p className="text-sm font-semibold text-violet-950">
          Escalar para o Plano Organizacional
        </p>
        <p className="mt-1 text-xs text-violet-900/80">
          A causa raiz exige uma iniciativa estrutural no plano TD do Chamelleon (mesmo backlog
          das sprints geradas pela IA).
        </p>
      </div>

      <label className="block text-sm">
        <span className="mb-1 block font-medium text-slate-700">Domínio organizacional</span>
        <select
          value={domain}
          onChange={(event) => setDomain(event.target.value)}
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
        >
          {TD_OFFICIAL_DOMAINS.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>

      {localError && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {localError}
        </p>
      )}

      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <button
          type="button"
          onClick={() => {
            setOpen(false);
            setLocalError('');
          }}
          className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="rounded-lg bg-violet-700 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-800 disabled:opacity-60"
        >
          {submitting ? 'Escalando…' : 'Confirmar escalada'}
        </button>
      </div>
    </form>
  );
}
