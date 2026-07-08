import VoiceTextarea from './VoiceTextarea';
import YesNoToggle from './YesNoToggle';

interface Props {
  label: string;
  value: boolean | null;
  onChange: (v: boolean) => void;
  details?: string;
  onDetailsChange?: (text: string) => void;
  detailsPlaceholder?: string;
  disabled?: boolean;
  onDictate?: (current: string, apply: (text: string) => void) => void;
  dictationSupported?: boolean;
  isListening?: boolean;
}

export default function YesNoWithDetails({
  label,
  value,
  onChange,
  details = '',
  onDetailsChange,
  detailsPlaceholder = 'Detalhes…',
  disabled = false,
  onDictate,
  dictationSupported = false,
  isListening = false,
}: Props) {
  const showDetails = value !== null && onDetailsChange;

  return (
    <div className="space-y-0">
      <YesNoToggle label={label} value={value} onChange={onChange} disabled={disabled} />
      {showDetails && (
        <div className="-mt-1 rounded-b-2xl border border-t-0 border-slate-200 bg-white px-3 pb-3">
          <VoiceTextarea
            label="Detalhamento"
            value={details}
            onChange={onDetailsChange}
            disabled={disabled}
            rows={2}
            placeholder={detailsPlaceholder}
            onDictate={onDictate}
            dictationSupported={dictationSupported}
            isListening={isListening}
          />
        </div>
      )}
    </div>
  );
}
