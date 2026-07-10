import { useEffect, useState } from 'react';
import { KAIZEN_STAGES } from '../../constants/kaizen';
import { updateKaizenTicket } from '../../services/kaizenApi';
import KaizenEscalatePanel from './KaizenEscalatePanel';

const STAGE_COPY = {
  Contencao: {
    title: 'Ação de contenção',
    description: 'Descreva a contenção adotada para estabilizar o processo antes da análise de causa.',
    field: 'temporary_containment_action',
    placeholder: 'Ex.: Isolar área, acionar fornecedor, redistribuir equipe...',
    submitLabel: 'Salvar e avançar para Contenção',
  },
  Padronizacao: {
    title: 'Padronização / plano definitivo',
    description: 'Registre o novo padrão ou plano de ação definitivo após a causa raiz.',
    field: 'standardization_action',
    placeholder: 'Ex.: Checklist revisado, treinamento padronizado, ponto de controle visual...',
    submitLabel: 'Salvar e avançar para Padronização',
  },
};

export default function KaizenStageTransitionModal({ transition, onClose, onCompleted, onEscalated }) {
  const [textValue, setTextValue] = useState('');
  const [isRetrained, setIsRetrained] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const { ticket, fromStage, toStage } = transition || {};
  const stageMeta = KAIZEN_STAGES.find((stage) => stage.id === toStage);
  const textConfig = STAGE_COPY[toStage];

  useEffect(() => {
    if (!ticket) return;
    setTextValue(
      toStage === 'Contencao'
        ? ticket.temporary_containment_action || ''
        : toStage === 'Padronizacao'
          ? ticket.standardization_action || ''
          : '',
    );
    setIsRetrained(
      typeof ticket.is_operator_retrained === 'boolean' ? ticket.is_operator_retrained : null,
    );
    setError('');
  }, [ticket, toStage]);

  if (!transition || !ticket) return null;

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError('');

    const payload = { workflow_stage: toStage };

    if (toStage === 'Contencao') {
      if (!textValue.trim()) {
        setError('Informe a ação de contenção adotada.');
        setSaving(false);
        return;
      }
      payload.temporary_containment_action = textValue.trim();
    }

    if (toStage === 'Padronizacao') {
      if (!textValue.trim()) {
        setError('Informe o novo padrão ou plano de ação definitivo.');
        setSaving(false);
        return;
      }
      payload.standardization_action = textValue.trim();
    }

    if (toStage === 'Concluido') {
      if (isRetrained === null) {
        setError('Confirme se o operador foi retreinado.');
        setSaving(false);
        return;
      }
      payload.is_operator_retrained = isRetrained;
    }

    try {
      const response = await updateKaizenTicket(ticket.id, payload);
      onCompleted?.({
        ticket: response.ticket || response,
        fromStage,
        toStage,
      });
      onClose?.();
    } catch (err) {
      setError(err.message || 'Não foi possível concluir a transição.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/50 p-4 sm:items-center">
      <button type="button" aria-label="Fechar modal" className="absolute inset-0" onClick={onClose} />

      <div className="relative z-10 w-full max-w-lg rounded-2xl bg-white shadow-2xl">
        <header className="border-b border-slate-100 px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Transição de fase · {stageMeta?.label || toStage}
          </p>
          <h2 className="mt-1 text-lg font-bold text-slate-900">{ticket.title}</h2>
        </header>

        <form onSubmit={handleSubmit} className="space-y-4 px-5 py-5">
          {textConfig && (
            <>
              <p className="text-sm text-slate-600">{textConfig.description}</p>
              <div>
                <label htmlFor="transition-text" className="mb-1.5 block text-sm font-semibold text-slate-700">
                  {textConfig.title}
                </label>
                <textarea
                  id="transition-text"
                  rows={4}
                  value={textValue}
                  onChange={(event) => setTextValue(event.target.value)}
                  placeholder={textConfig.placeholder}
                  className="w-full resize-none rounded-xl border border-slate-200 px-3 py-2.5 text-sm text-slate-800 shadow-sm outline-none ring-sky-200 transition focus:border-sky-400 focus:ring-2"
                />
              </div>
            </>
          )}

          {toStage === 'Concluido' && (
            <fieldset className="space-y-3">
              <legend className="text-sm font-semibold text-slate-700">Operador retreinado?</legend>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setIsRetrained(true)}
                  className={`flex-1 rounded-xl border px-4 py-2.5 text-sm font-semibold ${
                    isRetrained === true
                      ? 'border-emerald-500 bg-emerald-50 text-emerald-800'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  Sim
                </button>
                <button
                  type="button"
                  onClick={() => setIsRetrained(false)}
                  className={`flex-1 rounded-xl border px-4 py-2.5 text-sm font-semibold ${
                    isRetrained === false
                      ? 'border-amber-500 bg-amber-50 text-amber-900'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  Não
                </button>
              </div>
            </fieldset>
          )}

          {toStage === 'Padronizacao' &&
            !ticket.escalated_to_sprint_id &&
            !ticket.is_escalated && (
              <KaizenEscalatePanel
                ticketId={ticket.id}
                rootCauseAnalysis={ticket.root_cause_analysis}
                onSuccess={(response) => {
                  onEscalated?.(response);
                  onClose?.();
                }}
              />
            )}

          {error && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          <footer className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end">
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
              className="rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
            >
              {saving ? 'Salvando…' : textConfig?.submitLabel || 'Confirmar transição'}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
