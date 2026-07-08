import MicIcon from './icons/MicIcon';

export default function ContextDictationField({
  id,
  label,
  hint,
  placeholder,
  value,
  onChange,
  rows = 5,
  required = false,
  speechSupported,
  isMobile,
  isListening,
  isActiveField,
  fieldFlash,
  onToggleDictation,
  disabled = false,
}) {
  const listening = isListening && isActiveField;

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 sm:p-4">
      <div className="mb-3 space-y-2">
        <div>
          <label htmlFor={id} className="text-sm font-bold text-[#4A2E80] sm:text-base">
            {label}
            {required && <span className="ml-1 text-red-600">*</span>}
          </label>
          {hint && <p className="mt-1 text-xs leading-relaxed text-slate-500 sm:text-sm">{hint}</p>}
        </div>

        <button
          type="button"
          disabled={disabled || !speechSupported}
          onClick={() => onToggleDictation(id, value)}
          aria-pressed={listening}
          aria-label={`Ditado por voz — ${label}`}
          className={[
            'flex w-full min-h-[44px] items-center justify-center gap-2 rounded-xl border px-4 py-3 text-sm font-bold transition-colors touch-manipulation sm:w-auto sm:min-h-0 sm:rounded-full sm:px-4 sm:py-2 sm:text-xs',
            listening
              ? 'border-red-400 bg-red-50 text-red-700 shadow-[0_0_0_3px_rgba(239,68,68,0.2)]'
              : 'border-violet-300 bg-violet-50 text-violet-900 active:bg-violet-100',
            disabled || !speechSupported ? 'cursor-not-allowed opacity-45' : '',
          ].join(' ')}
        >
          <MicIcon className={listening ? 'h-5 w-5 animate-pulse' : 'h-5 w-5 sm:h-4 sm:w-4'} />
          <span>{listening ? 'Parar ditado' : 'Ditado por voz'}</span>
        </button>
      </div>

      <textarea
        id={id}
        rows={rows}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder={placeholder}
        autoComplete="off"
        autoCorrect="on"
        spellCheck
        enterKeyHint="done"
        className={[
          'w-full resize-y rounded-xl border px-3 py-3 leading-relaxed text-slate-800 transition-shadow touch-manipulation',
          'text-base sm:text-sm',
          listening
            ? 'border-violet-500 bg-white shadow-[0_0_0_3px_rgba(124,58,237,0.15)]'
            : fieldFlash
              ? 'border-emerald-500 bg-white shadow-[0_0_0_3px_rgba(5,150,105,0.18)]'
              : 'border-slate-200 bg-white',
        ].join(' ')}
        style={{ minHeight: isMobile ? '8rem' : undefined }}
      />
    </div>
  );
}
