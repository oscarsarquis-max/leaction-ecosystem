import { OCCURRENCE_TYPES } from '../constants/rdo';
import type { OccurrenceRow } from '../types';
import VoiceTextarea from './ui/VoiceTextarea';

interface Props {
  occurrences: OccurrenceRow[];
  onChange: (rows: OccurrenceRow[]) => void;
  disabled?: boolean;
  dictationSupported: boolean;
  isListening: boolean;
  onDictate: (current: string, apply: (text: string) => void) => void;
}

const EMPTY_DRAFT = (): OccurrenceRow => ({
  type: 'Geral',
  exact_location: '',
  what_happened: '',
  immediate_action_taken: '',
});

export default function OccurrencesPanel({
  occurrences,
  onChange,
  disabled = false,
  dictationSupported,
  isListening,
  onDictate,
}: Props) {
  const draft = occurrences.length > 0 ? null : EMPTY_DRAFT();
  const editing = occurrences.length > 0 ? occurrences[occurrences.length - 1] : draft!;
  const editingIndex = occurrences.length - 1;

  function patchDraft(patch: Partial<OccurrenceRow>) {
    if (occurrences.length === 0) {
      onChange([{ ...EMPTY_DRAFT(), ...patch }]);
      return;
    }
    onChange(
      occurrences.map((row, i) => (i === editingIndex ? { ...row, ...patch } : row)),
    );
  }

  function addAnother() {
    const last = occurrences[occurrences.length - 1];
    if (!last?.what_happened?.trim()) return;
    onChange([...occurrences, EMPTY_DRAFT()]);
  }

  function removeAt(index: number) {
    onChange(occurrences.filter((_, i) => i !== index));
  }

  return (
    <div className="mt-4 space-y-4">
      <p className="text-sm text-slate-600">
        Registre o que deu errado no canteiro. Fale como se estivesse explicando para o mestre de
        obras na beira da vala.
      </p>

      {occurrences.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {occurrences.map((_, idx) => (
            <button
              key={idx}
              type="button"
              disabled={disabled}
              onClick={() => {
                const copy = [...occurrences];
                const [item] = copy.splice(idx, 1);
                copy.push(item);
                onChange(copy);
              }}
              className={[
                'rounded-full px-3 py-1 text-xs font-bold',
                idx === editingIndex
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-100 text-slate-700',
              ].join(' ')}
            >
              Ocorrência {idx + 1}
            </button>
          ))}
        </div>
      )}

      <div>
        <p className="mb-2 text-sm font-bold text-slate-800">Que tipo de problema foi?</p>
        <div className="grid grid-cols-2 gap-2">
          {OCCURRENCE_TYPES.map((opt) => (
            <button
              key={opt.value}
              type="button"
              disabled={disabled}
              onClick={() => patchDraft({ type: opt.value })}
              className={[
                'min-h-12 rounded-xl border-2 px-2 text-sm font-bold',
                editing.type === opt.value
                  ? 'border-emerald-600 bg-emerald-600 text-white'
                  : 'border-slate-200 bg-white text-slate-800',
              ].join(' ')}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <VoiceTextarea
        label="Onde aconteceu?"
        value={editing.exact_location || ''}
        onChange={(t) => patchDraft({ exact_location: t })}
        placeholder="Ex: Bloco A, 2º Andar"
        rows={2}
        disabled={disabled}
        dictationSupported={dictationSupported}
        isListening={isListening}
        onDictate={onDictate}
      />
      <VoiceTextarea
        label="O que aconteceu exatamente?"
        value={editing.what_happened || ''}
        onChange={(t) => patchDraft({ what_happened: t })}
        placeholder="Descreva o problema físico"
        rows={3}
        disabled={disabled}
        dictationSupported={dictationSupported}
        isListening={isListening}
        onDictate={onDictate}
      />
      <VoiceTextarea
        label="O que você fez na hora para não parar o serviço?"
        value={editing.immediate_action_taken || ''}
        onChange={(t) => patchDraft({ immediate_action_taken: t })}
        placeholder="Ação imediata tomada"
        rows={3}
        disabled={disabled}
        dictationSupported={dictationSupported}
        isListening={isListening}
        onDictate={onDictate}
      />

      {!disabled && occurrences.length > 0 && editing.what_happened?.trim() && (
        <button
          type="button"
          onClick={addAnother}
          className="w-full min-h-12 rounded-xl border-2 border-dashed border-emerald-400 text-sm font-bold text-emerald-800"
        >
          + Registrar outra ocorrência
        </button>
      )}

      {!disabled && occurrences.length > 0 && (
        <button
          type="button"
          onClick={() => removeAt(editingIndex)}
          className="text-sm font-semibold text-red-600"
        >
          Remover esta ocorrência
        </button>
      )}
    </div>
  );
}
