import { useEffect, useState } from 'react';
import { parseOccurrenceFromTicket } from '../../utils/kaizenTicketMeta';
import { saveKaizenFiveWhys } from '../../services/kaizenApi';
import KaizenEscalatePanel from './KaizenEscalatePanel';

const WHY_FIELDS = [
  { key: 'why_1', label: 'Por que 1?' },
  { key: 'why_2', label: 'Por que 2?' },
  { key: 'why_3', label: 'Por que 3?' },
  { key: 'why_4', label: 'Por que 4?' },
  { key: 'why_5', label: 'Por que 5? (Causa Raiz)' },
];

export default function FiveWhysModal({
  ticket,
  open,
  onClose,
  onSaved,
  onEscalated,
  requireComplete = false,
  allowEscalate = true,
}) {
  const [form, setForm] = useState({
    why_1: '',
    why_2: '',
    why_3: '',
    why_4: '',
    why_5: '',
    root_cause: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!ticket) return;
    const analysis = ticket.root_cause_analysis || {};
    setForm({
      why_1: analysis.why_1 || '',
      why_2: analysis.why_2 || '',
      why_3: analysis.why_3 || '',
      why_4: analysis.why_4 || '',
      why_5: analysis.why_5 || '',
      root_cause: analysis.root_cause || '',
    });
    setError('');
  }, [ticket]);

  if (!open || !ticket) return null;

  const occurrence = parseOccurrenceFromTicket(ticket);

  function updateField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSave(event) {
    event.preventDefault();
    if (requireComplete && !form.why_1.trim() && !form.root_cause.trim()) {
      setError('Preencha pelo menos o 1º porquê ou a causa raiz para avançar.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const response = await saveKaizenFiveWhys(ticket.id, {
        ...form,
        root_cause: form.root_cause || form.why_5,
      });
      onSaved?.(response.ticket);
      onClose();
    } catch (err) {
      setError(err.message || 'Não foi possível salvar a análise.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/50 p-4 sm:items-center">
      <button
        type="button"
        aria-label="Fechar modal"
        className="absolute inset-0"
        onClick={onClose}
      />

      <div className="relative z-10 flex max-h-[92vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <header className="border-b border-slate-100 px-5 py-4 sm:px-6">
          <p className="text-xs font-semibold uppercase tracking-wider text-sky-600">
            Investigação — 5 Porquês
          </p>
          <h2 className="mt-1 text-lg font-bold text-slate-900">{ticket.title}</h2>
        </header>

        <form onSubmit={handleSave} className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5 sm:px-6">
            <section className="rounded-xl border border-orange-100 bg-orange-50/60 p-4">
              <p className="text-xs font-bold uppercase tracking-wider text-orange-800">
                Ocorrência original (RDO)
              </p>
              <dl className="mt-3 space-y-2 text-sm">
                <div>
                  <dt className="font-semibold text-slate-700">Onde</dt>
                  <dd className="text-slate-600">{occurrence.location}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-slate-700">O que aconteceu</dt>
                  <dd className="text-slate-600">{occurrence.whatHappened}</dd>
                </div>
                {occurrence.immediateAction && (
                  <div>
                    <dt className="font-semibold text-slate-700">Ação na hora</dt>
                    <dd className="text-slate-600">{occurrence.immediateAction}</dd>
                  </div>
                )}
              </dl>
            </section>

            <section className="space-y-3">
              {WHY_FIELDS.map((field, index) => (
                <div key={field.key}>
                  <label
                    htmlFor={field.key}
                    className="mb-1.5 block text-sm font-semibold text-slate-700"
                  >
                    {field.label}
                  </label>
                  <textarea
                    id={field.key}
                    rows={2}
                    value={form[field.key]}
                    onChange={(event) => updateField(field.key, event.target.value)}
                    placeholder="Descreva a causa imediata..."
                    className="w-full resize-none rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-slate-800 shadow-sm outline-none ring-sky-200 transition focus:border-sky-400 focus:ring-2"
                  />
                  {index < WHY_FIELDS.length - 1 && (
                    <p className="mt-2 text-center text-lg text-sky-400" aria-hidden="true">
                      ⬇️
                    </p>
                  )}
                </div>
              ))}

              <div>
                <label
                  htmlFor="root_cause"
                  className="mb-1.5 block text-sm font-semibold text-violet-800"
                >
                  Causa raiz confirmada
                </label>
                <textarea
                  id="root_cause"
                  rows={2}
                  value={form.root_cause}
                  onChange={(event) => updateField('root_cause', event.target.value)}
                  placeholder="Resumo da causa raiz (pode repetir o 5º porquê)"
                  className="w-full resize-none rounded-xl border border-violet-200 bg-violet-50/40 px-3 py-2.5 text-sm text-slate-800 shadow-sm outline-none ring-violet-200 transition focus:border-violet-400 focus:ring-2"
                />
              </div>
            </section>

            {error && (
              <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </p>
            )}

            {allowEscalate && !ticket.escalated_to_sprint_id && !ticket.is_escalated && (
              <KaizenEscalatePanel
                ticketId={ticket.id}
                rootCauseAnalysis={{
                  ...form,
                  root_cause: form.root_cause || form.why_5,
                }}
                disabled={!form.why_1.trim() && !form.root_cause.trim() && !form.why_5.trim()}
                onSuccess={(response) => {
                  onEscalated?.(response);
                  onClose();
                }}
              />
            )}
          </div>

          <footer className="flex shrink-0 flex-col-reverse gap-2 border-t border-slate-100 px-5 py-4 sm:flex-row sm:justify-end sm:px-6">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-xl bg-sky-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-700 disabled:opacity-60"
            >
              {saving ? 'Salvando...' : 'Salvar Análise'}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
