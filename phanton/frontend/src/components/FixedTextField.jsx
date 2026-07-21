/** Campo de texto de altura fixa — evita JSON/HTML estourarem a tela. */
const FIELD_CLASS =
  'block h-48 w-full resize-none overflow-auto rounded-xl border border-slate-700 bg-slate-950 p-3 font-mono text-xs leading-relaxed text-slate-100 outline-none focus:ring-2 focus:ring-sky-400'

export default function FixedTextField({
  value = '',
  onChange,
  readOnly = true,
  className = '',
  spellCheck = false,
  'aria-label': ariaLabel = 'Conteúdo',
}) {
  return (
    <textarea
      value={value}
      readOnly={readOnly}
      onChange={onChange}
      spellCheck={spellCheck}
      aria-label={ariaLabel}
      className={`${FIELD_CLASS} ${className}`}
    />
  )
}

export const FIXED_TEXT_HEIGHT_CLASS = 'h-48'
