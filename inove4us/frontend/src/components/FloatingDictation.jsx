import { useEffect, useRef, useState } from 'react'
import { useSpeechDictation } from './DictationField'

/**
 * Microfone flutuante — abre e já começa a ouvir; texto aparece na hora.
 */
export default function FloatingDictation({
  value,
  onChange,
  onSendToProblema,
  showSendToProblema = false,
}) {
  const [open, setOpen] = useState(false)
  const autoStartedRef = useRef(false)

  const { listening, supported, error, start, stop, toggle, setError } = useSpeechDictation({
    value: value || '',
    onChange,
    preserveNewlines: true,
  })

  useEffect(() => {
    if (!open) {
      autoStartedRef.current = false
      stop()
      return
    }
    if (!supported || autoStartedRef.current) return
    autoStartedRef.current = true
    // Abre o painel e começa a ouvir sem segundo clique.
    const t = window.setTimeout(() => start(), 80)
    return () => window.clearTimeout(t)
  }, [open, supported, start, stop])

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col items-end gap-3 print:hidden">
      {open && (
        <div className="w-[min(92vw,22rem)] rounded-2xl border border-brand-200 bg-white p-4 shadow-soft animate-fade-in">
          <div className="mb-3 flex items-center justify-between gap-2">
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-bordo">
              Ditado por voz
            </p>
            <button
              type="button"
              className="text-xs font-semibold text-bordo-soft hover:text-bordo"
              onClick={() => {
                stop()
                setOpen(false)
              }}
            >
              Fechar
            </button>
          </div>

          <div className="relative">
            <textarea
              rows={4}
              className="field-input resize-y pr-12 text-sm"
              placeholder="Fale agora — o texto aparece aqui…"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              autoFocus
            />
            {supported ? (
              <button
                type="button"
                onClick={() => {
                  setError('')
                  toggle()
                }}
                title={listening ? 'Parar ditado' : 'Ditar por microfone'}
                aria-label={listening ? 'Parar ditado' : 'Ditar por microfone'}
                aria-pressed={listening}
                className={[
                  'absolute right-2 top-2.5 flex h-9 w-9 items-center justify-center rounded-lg transition',
                  listening
                    ? 'bg-brand-600 text-white shadow-soft ring-2 ring-brand-200'
                    : 'bg-brand-50 text-bordo hover:bg-brand-100',
                ].join(' ')}
              >
                {listening ? (
                  <span className="relative flex h-3 w-3">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white/70" />
                    <span className="relative inline-flex h-3 w-3 rounded-full bg-white" />
                  </span>
                ) : (
                  <i className="fa-solid fa-microphone text-sm" />
                )}
              </button>
            ) : null}
          </div>

          {listening ? (
            <p className="mt-1.5 text-[11px] font-semibold text-brand-600">
              Ouvindo… continue falando. Clique no microfone para encerrar.
            </p>
          ) : null}
          {error ? <p className="mt-1.5 text-[11px] text-bordo">{error}</p> : null}

          {showSendToProblema && value?.trim() && (
            <button
              type="button"
              className="btn-primary mt-3 w-full !py-2 text-xs"
              onClick={() => {
                stop()
                onSendToProblema?.(value)
                setOpen(false)
              }}
            >
              Usar no problema
            </button>
          )}
        </div>
      )}

      <button
        type="button"
        onClick={() => {
          if (open) {
            stop()
            setOpen(false)
          } else {
            setOpen(true)
          }
        }}
        title="Ditado por microfone"
        aria-label="Abrir ditado por microfone"
        aria-expanded={open}
        className={[
          'flex h-14 w-14 items-center justify-center rounded-full shadow-soft transition',
          open || listening
            ? 'bg-bordo text-white ring-4 ring-brand-200'
            : 'bg-brand-600 text-white hover:bg-brand-700',
        ].join(' ')}
      >
        <i className={`fa-solid ${open ? 'fa-xmark' : 'fa-microphone'} text-lg`} />
      </button>
    </div>
  )
}
