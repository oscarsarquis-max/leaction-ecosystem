interface Props {
  label: string;
  value: number;
  onChange: (value: number) => void;
  details?: string;
  onDetailsChange?: (text: string) => void;
  detailsPlaceholder?: string;
  disabled?: boolean;
  min?: number;
  max?: number;
  onDictate?: (current: string, apply: (text: string) => void) => void;
  dictationSupported?: boolean;
  isListening?: boolean;
}

export default function MetricWithDetails({
  label,
  value,
  onChange,
  details = '',
  onDetailsChange,
  detailsPlaceholder = 'Detalhes…',
  disabled = false,
  min = 0,
  max = 999,
  onDictate,
  dictationSupported = false,
  isListening = false,
}: Props) {
  const showDetails = value > 0 && onDetailsChange;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="min-w-0 flex-1 text-sm font-semibold leading-snug text-slate-800">{label}</p>
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            disabled={disabled || value <= min}
            onClick={() => onChange(Math.max(min, value - 1))}
            className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 text-xl font-bold text-slate-800 disabled:opacity-40"
            aria-label={`Diminuir ${label}`}
          >
            −
          </button>
          <span className="w-8 text-center text-2xl font-bold text-emerald-700">{value}</span>
          <button
            type="button"
            disabled={disabled || value >= max}
            onClick={() => onChange(Math.min(max, value + 1))}
            className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-600 text-xl font-bold text-white disabled:opacity-40"
            aria-label={`Aumentar ${label}`}
          >
            +
          </button>
        </div>
      </div>

      {showDetails && (
        <div className="mt-2 border-t border-slate-100 pt-2">
          <div className="mb-1 flex items-center justify-end">
            {dictationSupported && onDictate && !disabled && (
              <button
                type="button"
                onClick={() => onDictate(details, onDetailsChange)}
                className={[
                  'flex h-10 w-10 items-center justify-center rounded-lg text-lg',
                  isListening
                    ? 'bg-red-600 text-white animate-pulse'
                    : 'bg-emerald-50 text-emerald-900 ring-1 ring-emerald-200',
                ].join(' ')}
                aria-label="Ditado por voz"
              >
                🎤
              </button>
            )}
          </div>
          <textarea
            value={details}
            onChange={(e) => onDetailsChange(e.target.value)}
            disabled={disabled}
            rows={2}
            placeholder={detailsPlaceholder}
            className="w-full resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none ring-emerald-500 focus:ring-2 disabled:bg-slate-50"
          />
        </div>
      )}
    </div>
  );
}
