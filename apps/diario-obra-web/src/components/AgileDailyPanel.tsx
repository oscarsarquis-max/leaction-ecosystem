import VoiceTextarea from './ui/VoiceTextarea';
import YesNoToggle from './ui/YesNoToggle';

interface Props {
  sprintDailyGoal: string;
  goalAchieved: boolean | null;
  impedimentDetails: string;
  mitigationAction: string;
  preventiveAction: string;
  onSprintDailyGoalChange: (value: string) => void;
  onGoalAchievedChange: (value: boolean) => void;
  onImpedimentDetailsChange: (value: string) => void;
  onMitigationActionChange: (value: string) => void;
  onPreventiveActionChange: (value: string) => void;
  sprintGoalLocked?: boolean;
  disabled?: boolean;
  dictationSupported?: boolean;
  isListening?: boolean;
  onDictate?: (current: string, apply: (text: string) => void) => void;
}

export function dailyGoalAnswered(goalAchieved: boolean | null) {
  return goalAchieved !== null;
}

/** Exige Daily Ágil só quando há meta planejada / bloqueada ou resposta iniciada. */
export function dailyGoalRequired(opts: {
  sprintDailyGoal?: string;
  sprintGoalLocked?: boolean;
  goalAchieved?: boolean | null;
  impedimentDetails?: string;
  mitigationAction?: string;
  preventiveAction?: string;
}) {
  return Boolean(
    (opts.sprintDailyGoal || '').trim() ||
      opts.sprintGoalLocked ||
      opts.goalAchieved != null ||
      (opts.impedimentDetails || '').trim() ||
      (opts.mitigationAction || '').trim() ||
      (opts.preventiveAction || '').trim(),
  );
}

export default function AgileDailyPanel({
  sprintDailyGoal,
  goalAchieved,
  impedimentDetails,
  mitigationAction,
  preventiveAction,
  onSprintDailyGoalChange,
  onGoalAchievedChange,
  onImpedimentDetailsChange,
  onMitigationActionChange,
  onPreventiveActionChange,
  sprintGoalLocked = false,
  disabled = false,
  dictationSupported = false,
  isListening = false,
  onDictate,
}: Props) {
  function handleGoalChange(value: boolean) {
    onGoalAchievedChange(value);
    if (value) {
      onImpedimentDetailsChange('');
      onMitigationActionChange('');
      onPreventiveActionChange('');
    }
  }

  return (
    <div className="mt-4 space-y-4">
      {sprintGoalLocked ? (
        <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-sky-700">🎯 Meta do Dia</p>
          <p className="mt-2 text-base font-medium text-slate-800">
            {sprintDailyGoal || 'Meta ainda não definida pelo gestor.'}
          </p>
          <p className="mt-1 text-xs text-sky-600">Definida no planejamento central (somente leitura).</p>
        </div>
      ) : (
        <VoiceTextarea
          label="🎯 Meta do Dia (Sprint)"
          value={sprintDailyGoal}
          onChange={onSprintDailyGoalChange}
          disabled={disabled}
          rows={2}
          placeholder="Ex: Concluir armação do bloco B, 2º pavimento…"
          dictationSupported={dictationSupported}
          isListening={isListening}
          onDictate={onDictate}
        />
      )}

      <YesNoToggle
        label="Atingiu o resultado de hoje?"
        value={goalAchieved}
        onChange={handleGoalChange}
        disabled={disabled}
      />

      {goalAchieved === true && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-center">
          <p className="text-lg font-bold text-emerald-800">Excelente trabalho!</p>
          <p className="mt-1 text-sm text-emerald-700">Meta do dia cumprida. Seguimos no ritmo.</p>
        </div>
      )}

      {goalAchieved === false && (
        <div className="space-y-3 rounded-2xl border border-amber-200 bg-amber-50/50 p-3">
          <p className="px-1 text-sm font-semibold text-amber-900">
            Vamos entender o que travou e como destravar:
          </p>
          <VoiceTextarea
            label="Qual foi o impeditivo?"
            value={impedimentDetails}
            onChange={onImpedimentDetailsChange}
            disabled={disabled}
            rows={3}
            placeholder="O que impediu de bater a meta hoje?"
            dictationSupported={dictationSupported}
            isListening={isListening}
            onDictate={onDictate}
          />
          <VoiceTextarea
            label="O que você fez/fará para mitigar (solução rápida)?"
            value={mitigationAction}
            onChange={onMitigationActionChange}
            disabled={disabled}
            rows={3}
            placeholder="Ação imediata para não parar o serviço…"
            dictationSupported={dictationSupported}
            isListening={isListening}
            onDictate={onDictate}
          />
          <VoiceTextarea
            label="O que fazer para não acontecer de novo (ação preventiva)?"
            value={preventiveAction}
            onChange={onPreventiveActionChange}
            disabled={disabled}
            rows={3}
            placeholder="Como evitar esse impeditivo amanhã?"
            dictationSupported={dictationSupported}
            isListening={isListening}
            onDictate={onDictate}
          />
        </div>
      )}
    </div>
  );
}
