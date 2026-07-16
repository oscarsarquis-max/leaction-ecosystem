import { useState } from 'react'
import DictationField from './DictationField'

/**
 * Microfone flutuante disponível em qualquer etapa do fluxo.
 * Abre um bloco de anotações ditadas (pt-BR).
 */
export default function FloatingDictation({
  value,
  onChange,
  onSendToProblema,
  showSendToProblema = false,
}) {
  const [open, setOpen] = useState(false)

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
              onClick={() => setOpen(false)}
            >
              Fechar
            </button>
          </div>
          <DictationField
            as="textarea"
            rows={4}
            className="field-input resize-y text-sm"
            placeholder="Toque no microfone e fale…"
            value={value}
            onChange={onChange}
            autoFocus
          />
          {showSendToProblema && value?.trim() && (
            <button
              type="button"
              className="btn-primary mt-3 w-full !py-2 text-xs"
              onClick={() => {
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
        onClick={() => setOpen((v) => !v)}
        title="Ditado por microfone"
        aria-label="Abrir ditado por microfone"
        aria-expanded={open}
        className={[
          'flex h-14 w-14 items-center justify-center rounded-full shadow-soft transition',
          open
            ? 'bg-bordo text-white ring-4 ring-brand-200'
            : 'bg-brand-600 text-white hover:bg-brand-700',
        ].join(' ')}
      >
        <i className={`fa-solid ${open ? 'fa-xmark' : 'fa-microphone'} text-lg`} />
      </button>
    </div>
  )
}
