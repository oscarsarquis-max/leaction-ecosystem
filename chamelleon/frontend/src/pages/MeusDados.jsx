import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { activateClientProject, saveClientContext } from '../services/api';
import { useAuth } from '../context/AuthContext';
import JourneyStepper from '../components/JourneyStepper';
import ContextDictationField from '../components/ContextDictationField';
import { useVoiceDictation } from '../hooks/useVoiceDictation';
import {
  buildContextPayload,
  CONTEXT_FIELDS,
  contextIsComplete,
  readContextFromJourney,
} from '../utils/businessContext';
import { resolveJourneyFlags } from '../utils/journeyState';

export default function MeusDados() {
  const { journey, refreshProfile } = useAuth();
  const flags = resolveJourneyFlags(journey);
  const ctx = journey?.context_data || {};

  const [values, setValues] = useState(() => readContextFromJourney(ctx));
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    setValues(readContextFromJourney(ctx));
  }, [journey?.context_data]);

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

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    setMessage('');

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
      await refreshProfile();
      setMessage('Contexto empresarial salvo. Status avançado para CONTEXTO OK.');
    } catch (err) {
      setError(err.message || 'Erro ao salvar contexto.');
    } finally {
      setSaving(false);
    }
  }

  async function handleActivateProject() {
    setSaving(true);
    setError('');
    try {
      await activateClientProject();
      await refreshProfile();
      setMessage('Projeto ativado (PROJETO OK).');
    } catch (err) {
      setError(err.message || 'Erro ao ativar projeto.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 pb-28 sm:space-y-6 sm:pb-8">
      <div>
        <Link to="/" className="text-sm font-medium text-chameleon-dark hover:underline">
          ← Voltar ao painel
        </Link>
        <h1 className="mt-2 text-xl font-bold text-slate-900 sm:text-2xl">Contexto Empresarial</h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-600">{helpText}</p>
        {speechSupported && speechEnv.isMobile && (
          <p className="mt-1 text-xs text-slate-500">
            {speechEnv.platformLabel} · diga <strong>fim</strong> ou toque em Parar para encerrar
          </p>
        )}
      </div>

      <JourneyStepper steps={flags.steps} />

      {!speechSupported && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-relaxed text-amber-900">
          {helpText}
        </p>
      )}

      {dictationStatus && !isListening && (
        <p className="text-sm text-slate-600" aria-live="polite">
          {dictationStatus}
        </p>
      )}

      <form
        onSubmit={handleSave}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"
      >
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
        {message && (
          <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            {message}
          </p>
        )}

        <div className="flex flex-col gap-3 border-t border-slate-100 pt-4 sm:flex-row sm:flex-wrap">
          <button
            type="submit"
            disabled={saving}
            className="min-h-[48px] w-full rounded-xl bg-chameleon px-4 py-3 text-sm font-semibold text-white hover:bg-chameleon-dark disabled:opacity-60 sm:w-auto sm:min-h-0 sm:rounded-lg sm:py-2 touch-manipulation"
          >
            {saving ? 'Salvando...' : 'Salvar contexto'}
          </button>
          {!flags.isProjetoOk && (
            <button
              type="button"
              disabled={saving}
              onClick={handleActivateProject}
              className="min-h-[48px] w-full rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900 hover:bg-amber-100 sm:w-auto sm:min-h-0 sm:rounded-lg sm:py-2 touch-manipulation"
            >
              Simular contratação (PROJETO OK)
            </button>
          )}
        </div>
      </form>

      {isListening && (
        <div
          className="fixed inset-x-0 bottom-0 z-50 border-t border-red-200 bg-gradient-to-r from-red-50 to-violet-50 px-4 py-3 shadow-lg sm:static sm:rounded-xl sm:border sm:shadow-none"
          style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}
          role="status"
        >
          <div className="mx-auto flex max-w-3xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm font-semibold text-[#4A2E80]">
              Gravando… Toque em <strong>Parar</strong> ou diga <strong>fim</strong>
            </p>
            <button
              type="button"
              onClick={stopDictation}
              className="flex min-h-[48px] w-full items-center justify-center rounded-xl bg-red-600 px-6 py-3 text-sm font-bold text-white shadow active:bg-red-700 sm:w-auto sm:min-h-0 sm:rounded-full sm:py-2 touch-manipulation"
            >
              Parar ditado
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
