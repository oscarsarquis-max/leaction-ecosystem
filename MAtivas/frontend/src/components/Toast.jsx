import { useEffect } from 'react'
import { CheckCircle } from 'lucide-react'

function Toast({ mensagem, visivel, onOcultar, duracaoMs = 4000 }) {
  useEffect(() => {
    if (!visivel) return undefined
    const timer = window.setTimeout(() => onOcultar?.(), duracaoMs)
    return () => window.clearTimeout(timer)
  }, [visivel, duracaoMs, onOcultar])

  if (!visivel || !mensagem) return null

  return (
    <div
      className="fixed bottom-6 left-1/2 z-[60] flex w-[calc(100%-2rem)] max-w-sm -translate-x-1/2 items-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-medium text-white shadow-lg ring-1 ring-emerald-500/30"
      role="status"
      aria-live="polite"
    >
      <CheckCircle size={18} className="shrink-0" />
      <span>{mensagem}</span>
    </div>
  )
}

export default Toast
