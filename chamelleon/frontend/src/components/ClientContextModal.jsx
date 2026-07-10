import { useCallback, useEffect, useState } from 'react';
import { saveClientContext } from '../services/api';
import { useAuth } from '../context/AuthContext';
import ContextDictationField from './ContextDictationField';
import { useVoiceDictation } from '../hooks/useVoiceDictation';
import {
  buildContextPayload,
  CONTEXT_FIELDS,
  contextIsComplete,
  readContextFromJourney,
} from '../utils/businessContext';

export default function ClientContextModal({ open, onClose, onSaved, title }) {
  const { journey, refreshProfile } = useAuth();

  const [values, setValues] = useState(() => readContextFromJourney(journey?.context_data || {}));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (open) {
      setValues(readContextFromJourney(journey?.context_data));
      setError('');
    }
  }, [open, journey?.context_data]);

  const handleDictationValue = useCallback((fieldId, newValue) => {
    setValues((prev) => ({ ...prev, [fieldId]: newValue }));
  }, []);

  const {
    status: dictationStatus,
    isListening,
    activeFieldId,
    fieldHighlight,
    speechSupported,
    speechEnv,
    helpText,
    toggleDictation,
    stopDictation,
  } = useVoiceDictation({ onValueChange: handleDictationValue, disabled: saving });

  if (!open) return null;

  async function handleSave(event) {
    event.preventDefault();
    setSaving(true);
    setError('');

    if (!contextIsComplete(values)) {
      setError(
        'Preencha os três domínios com pelo menos 40 caracteres cada (digite ou use Ditado).',
      );
      setSaving(false);
      return;
    }

    try {
      if (isListening) stopDictation();
      await saveClientContext(buildContextPayload(values));
      await refreshProfile({ background: true });
      onSaved?.();
      onClose?.();
    } catch (err) {
      setError(err.message || 'Erro ao salvar contexto.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/50 p-0 sm:items-center sm:p-4">
      <div
        className="flex max-h-[92vh] w-full max-w-2xl flex-col overflow-hidden rounded-t-2xl border border-violet-200 bg-white shadow-2xl sm:rounded-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="context-modal-title"
      >
        <div className="border-b border-violet-100 bg-gradient-to-r from-violet-50 to-amber-50 px-5 py-4 sm:px-6">
          <p className="text-xs font-bold uppercase tracking-wider text-amber-600">Insight Gate</p>
          <h2 id="context-modal-title" className="mt-1 text-lg font-bold text-[#4A2E80] sm:text-xl">
            {title || 'Contexto institucional para a IA'}
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            A Gênese do plano de Transformação Digital precisa entender mercado, clientes e clima
            organizacional. Você pode ditatar ou digitar cada bloco.
          </p>
        </div>

        <form onSubmit={handleSave} className="flex min-h-0 flex-1 flex-col">
          <div className="space-y-4 overflow-y-auto px-5 py-4 sm:px-6">
            {!speechSupported && (
              <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                {helpText}
              </p>
            )}
            {dictationStatus && !isListening && (
              <p className="text-sm text-slate-600" aria-live="polite">
                {dictationStatus}
              </p>
            )}

            {CONTEXT_FIELDS.map((field) => (
              <ContextDictationField
                key={field.id}
                id={field.id}
                label={field.label}
                hint={field.hint}
                placeholder={field.placeholder}
                value={values[field.id] || ''}
                onChange={(v) => setValues((prev) => ({ ...prev, [field.id]: v }))}
                required
                disabled={saving}
                speechSupported={speechSupported}
                isMobile={speechEnv.isMobile}
                isListening={isListening}
                isActiveField={activeFieldId === field.id}
                fieldFlash={fieldHighlight?.id === field.id && fieldHighlight?.flash}
                onToggleDictation={toggleDictation}
              />
            ))}

            {error && (
              <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                {error}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-2 border-t border-slate-100 bg-slate-50 px-5 py-4 sm:flex-row sm:justify-end sm:px-6">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="min-h-[44px] rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
            >
              Preencher depois
            </button>
            <button
              type="submit"
              disabled={saving}
              className="min-h-[44px] rounded-xl bg-chameleon px-6 py-2.5 text-sm font-bold text-white hover:bg-chameleon-dark disabled:opacity-60"
            >
              {saving ? 'Salvando…' : 'Salvar contexto'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
