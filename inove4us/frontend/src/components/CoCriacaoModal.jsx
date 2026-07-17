import { useEffect, useState } from 'react'
import { api } from '../lib/api'

const TIPO_OPTIONS = [
  { value: 'ideia', label: 'Ideia de Metodologia' },
  { value: 'melhoria', label: 'Sugestão de Funcionalidade' },
  { value: 'bug', label: 'Reporte de Erro/Bug' },
]

/**
 * Modal do Programa de Co-criação — ideias e feedbacks dos professores.
 */
export default function CoCriacaoModal({ open, onClose, onSuccess }) {
  const [tipo, setTipo] = useState('ideia')
  const [mensagem, setMensagem] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    setTipo('ideia')
    setMensagem('')
    setError('')
    setLoading(false)
  }, [open])

  if (!open) return null

  async function handleSubmit(event) {
    event.preventDefault()
    const text = mensagem.trim()
    if (!text) {
      setError('Conte um pouco mais — a mensagem é obrigatória.')
      return
    }
    setLoading(true)
    setError('')
    try {
      await api.enviarFeedback({ tipo, mensagem: text })
      setMensagem('')
      setTipo('ideia')
      onSuccess?.()
      onClose?.()
    } catch (err) {
      setError(err.message || 'Não foi possível enviar. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end justify-center bg-bordo-deep/45 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cocriacao-title"
      onClick={(e) => {
        if (e.target === e.currentTarget && !loading) onClose?.()
      }}
    >
      <div className="relative w-full max-w-lg overflow-hidden rounded-2xl border border-amber-200/80 bg-gradient-to-b from-amber-50 via-white to-rose-50/40 shadow-soft sm:p-0">
        <div className="pointer-events-none absolute -right-10 -top-10 h-36 w-36 rounded-full bg-amber-300/30 blur-2xl" />
        <div className="pointer-events-none absolute -bottom-12 -left-8 h-32 w-32 rounded-full bg-rose-300/25 blur-2xl" />

        <form onSubmit={handleSubmit} className="relative p-5 sm:p-7">
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-amber-700">
            Programa de Co-criação
          </p>
          <h2
            id="cocriacao-title"
            className="mt-2 font-display text-2xl font-bold leading-snug text-bordo-deep"
          >
            Ajude a construir o inove4us! 🚀
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-bordo-soft">
            Teve uma ideia brilhante de metodologia? Sentiu falta de algum recurso? Envie para nós!
            Se sua sugestão entrar no nosso roteiro, você ganha{' '}
            <strong className="font-semibold text-bordo">10 planejamentos Premium</strong> como
            agradecimento.
          </p>

          <label className="mt-5 block space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-bordo-soft">
              Tipo de Mensagem
            </span>
            <select
              value={tipo}
              onChange={(e) => setTipo(e.target.value)}
              disabled={loading}
              className="w-full rounded-xl border border-amber-200/80 bg-white px-3 py-2.5 text-sm text-bordo outline-none ring-amber-200 focus:ring-2 disabled:opacity-60"
            >
              {TIPO_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <label className="mt-4 block space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-wide text-bordo-soft">
              Mensagem
            </span>
            <textarea
              value={mensagem}
              onChange={(e) => setMensagem(e.target.value)}
              required
              rows={6}
              disabled={loading}
              placeholder="Descreva sua ideia com o máximo de detalhes..."
              className="w-full resize-y rounded-xl border border-amber-200/80 bg-white px-3 py-2.5 text-sm leading-relaxed text-bordo outline-none ring-amber-200 placeholder:text-bordo-soft/60 focus:ring-2 disabled:opacity-60"
            />
          </label>

          {error ? (
            <p className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
              {error}
            </p>
          ) : null}

          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              className="btn-ghost !px-4 !py-2.5 text-sm"
              disabled={loading}
              onClick={onClose}
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-amber-500 to-rose-500 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:from-amber-400 hover:to-rose-400 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {loading ? 'Enviando…' : 'Enviar Ideia'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
