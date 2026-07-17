import { useEffect, useState } from 'react'
import CoCriacaoModal from './CoCriacaoModal'

/**
 * FAB + modal + toast do Programa de Co-criação (áreas autenticadas).
 */
export default function CoCriacaoEntry() {
  const [open, setOpen] = useState(false)
  const [toast, setToast] = useState('')

  useEffect(() => {
    if (!toast) return undefined
    const t = window.setTimeout(() => setToast(''), 4500)
    return () => window.clearTimeout(t)
  }, [toast])

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-4 z-40 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-amber-500/30 transition hover:scale-[1.03] hover:shadow-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-300 sm:bottom-8 sm:right-8"
        aria-label="Enviar ideia — Programa de Co-criação"
      >
        <span aria-hidden className="text-base leading-none">
          💡
        </span>
        Enviar Ideia
      </button>

      <CoCriacaoModal
        open={open}
        onClose={() => setOpen(false)}
        onSuccess={() =>
          setToast('Obrigado! Sua ideia foi enviada para nossos especialistas.')
        }
      />

      {toast ? (
        <div
          role="status"
          className="fixed bottom-24 left-1/2 z-[110] w-[min(92vw,28rem)] -translate-x-1/2 animate-fade-in rounded-2xl border border-emerald-200 bg-white px-4 py-3 text-center text-sm font-medium text-emerald-900 shadow-soft sm:bottom-28"
        >
          {toast}
        </div>
      ) : null}
    </>
  )
}
