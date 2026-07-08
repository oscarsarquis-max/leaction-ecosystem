interface Props {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  rows?: number;
  disabled?: boolean;
  onDictate?: (current: string, apply: (text: string) => void) => void;
  dictationSupported?: boolean;
  isListening?: boolean;
}

export default function VoiceTextarea({
  label,
  value,
  onChange,
  placeholder,
  rows = 4,
  disabled = false,
  onDictate,
  dictationSupported = false,
  isListening = false,
}: Props) {
  return (
    <div className="mt-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-sm font-bold uppercase tracking-wide text-emerald-800">{label}</span>
        {dictationSupported && onDictate && !disabled && (
          <button
            type="button"
            onClick={() => onDictate(value, onChange)}
            className={[
              'flex min-h-11 min-w-11 items-center justify-center rounded-xl px-3 text-xl shadow-sm',
              isListening
                ? 'bg-red-600 text-white animate-pulse'
                : 'bg-emerald-100 text-emerald-900 ring-1 ring-emerald-300',
            ].join(' ')}
            aria-label="Ditado por voz"
          >
            🎤
          </button>
        )}
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={rows}
        disabled={disabled}
        placeholder={placeholder}
        className="w-full rounded-2xl border border-slate-200 px-3 py-3 text-base outline-none ring-emerald-500 focus:ring-2 disabled:bg-slate-100"
      />
    </div>
  );
}
