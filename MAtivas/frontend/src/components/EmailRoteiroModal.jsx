import { useEffect, useState } from 'react'
import { Loader2, Mail, X } from 'lucide-react'
import { enviarRoteiroEmail } from '../services/api.js'

function EmailRoteiroModal({ aberto, onFechar, emailInicial = '', projectId, onSucesso }) {
  const [emailDestino, setEmailDestino] = useState(emailInicial)
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState('')

  useEffect(() => {
    if (aberto) {
      setEmailDestino(emailInicial || '')
      setErro('')
      setEnviando(false)
    }
  }, [aberto, emailInicial])

  if (!aberto) return null

  const fechar = () => {
    if (enviando) return
    onFechar()
  }

  const handleEnviar = async (e) => {
    e.preventDefault()
    const destino = emailDestino.trim().toLowerCase()

    if (!destino || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(destino)) {
      setErro('Informe um endereço de e-mail válido.')
      return
    }
    if (!projectId) {
      setErro('Roteiro não identificado. Gere o roteiro pelo fluxo completo.')
      return
    }

    setEnviando(true)
    setErro('')

    try {
      await enviarRoteiroEmail(destino, projectId)
      setEmailDestino('')
      onSucesso?.()
      onFechar()
    } catch (err) {
      const mensagem =
        err?.response?.data?.erro ||
        err?.response?.data?.detalhe ||
        err?.message ||
        'Não foi possível enviar o e-mail. Tente novamente.'
      setErro(mensagem)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="email-roteiro-titulo"
      onClick={fechar}
    >
      <div
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl ring-1 ring-slate-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
              <Mail size={18} />
            </span>
            <h2 id="email-roteiro-titulo" className="text-lg font-semibold text-slate-900">
              Receber Roteiro por E-mail
            </h2>
          </div>
          <button
            type="button"
            onClick={fechar}
            disabled={enviando}
            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50"
            aria-label="Fechar"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleEnviar} className="space-y-4">
          <label className="block text-sm font-medium text-slate-700">
            E-mail de destino
            <input
              type="email"
              value={emailDestino}
              onChange={(e) => setEmailDestino(e.target.value)}
              placeholder="professor@escola.edu.br"
              disabled={enviando}
              autoFocus
              className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30 disabled:bg-slate-50"
            />
          </label>

          {erro && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-100">
              {erro}
            </p>
          )}

          <div className="flex justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={fechar}
              disabled={enviando}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={enviando}
              className="inline-flex min-w-[108px] items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:opacity-60"
            >
              {enviando ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Enviando...
                </>
              ) : (
                'Enviar'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default EmailRoteiroModal
