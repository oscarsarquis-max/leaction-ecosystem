import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { NINA_AVATAR_SRC } from '../lib/ninaAvatar'
import UpgradeCreditsModal from './UpgradeCreditsModal'

function NinaAvatar({ className = 'h-7 w-7', alt = '' }) {
  return (
    <span
      aria-hidden={!alt}
      className={`inline-flex shrink-0 overflow-hidden rounded-full bg-[#4a3428] ring-2 ring-white/40 ${className}`}
    >
      <img
        src={NINA_AVATAR_SRC}
        alt={alt}
        className="h-full w-full object-contain object-top"
      />
    </span>
  )
}

/**
 * Assistente por árvore de decisão + campo de sugestão (Programa de Co-criação).
 * Navegação dos botões é 100% local após carregar a árvore (Hub ou fallback).
 * Envio de sugestão continua em POST /api/feedbacks (crédito por revisão, status pendente).
 */
export default function AssistenteChat() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [tree, setTree] = useState(null)
  const [nodeId, setNodeId] = useState('inicio')
  const [loadError, setLoadError] = useState('')
  const [sugestao, setSugestao] = useState('')
  const [sending, setSending] = useState(false)
  const [toast, setToast] = useState('')
  const [upgradeHint, setUpgradeHint] = useState(false)
  const [showUpgrade, setShowUpgrade] = useState(false)

  const loadTree = useCallback(async () => {
    setLoadError('')
    try {
      const data = await api.getAssistenteChat()
      const t = data?.tree
      if (t?.nodes && t.root_id) {
        setTree(t)
        setNodeId(t.root_id)
      } else {
        setLoadError('Não foi possível carregar o guia.')
      }
    } catch (err) {
      setLoadError(err.message || 'Falha ao carregar o assistente.')
    }
  }, [])

  useEffect(() => {
    if (!open) return
    if (tree) return
    void loadTree()
  }, [open, tree, loadTree])

  useEffect(() => {
    if (!toast) return undefined
    const t = window.setTimeout(() => setToast(''), 4500)
    return () => window.clearTimeout(t)
  }, [toast])

  const avatarName = tree?.avatar_name || 'Nina'
  const node = tree?.nodes?.[nodeId] || null

  function handleOption(opt) {
    if (!opt) return
    if (opt.action === 'open_upgrade') {
      setUpgradeHint(true)
      setShowUpgrade(true)
      return
    }
    if (opt.href && opt.href.startsWith('/')) {
      setOpen(false)
      navigate(opt.href)
      if (opt.next) setNodeId(opt.next)
      return
    }
    if (opt.next && tree?.nodes?.[opt.next]) {
      setNodeId(opt.next)
    }
  }

  async function handleSendSugestao(e) {
    e?.preventDefault?.()
    const text = sugestao.trim()
    if (!text || sending) return
    setSending(true)
    try {
      await api.enviarFeedback({ tipo: 'melhoria', mensagem: text })
      setSugestao('')
      setToast('Recebemos sua sugestão, obrigado!')
    } catch (err) {
      setToast(err.message || 'Não foi possível enviar. Tente novamente.')
    } finally {
      setSending(false)
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-4 z-40 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-amber-500/30 transition hover:scale-[1.03] hover:shadow-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-300 sm:bottom-8 sm:right-8"
        aria-label="Abrir assistente Nina"
      >
        <NinaAvatar className="h-8 w-8" />
        Assistente
      </button>

      {open ? (
        <div
          className="fixed inset-0 z-[100] flex items-end justify-end bg-bordo-deep/35 p-3 sm:p-6"
          role="dialog"
          aria-modal="true"
          aria-labelledby="assistente-title"
          onClick={(e) => {
            if (e.target === e.currentTarget && !sending) setOpen(false)
          }}
        >
          <div className="flex max-h-[min(88vh,640px)] w-full max-w-md flex-col overflow-hidden rounded-2xl border border-amber-200/80 bg-gradient-to-b from-amber-50 via-white to-rose-50/50 shadow-soft">
            <header className="flex items-start justify-between gap-3 border-b border-amber-100/80 px-4 py-3">
              <div className="flex items-center gap-3">
                <NinaAvatar className="h-11 w-11 shadow-sm" alt={avatarName} />
                <div>
                  <h2
                    id="assistente-title"
                    className="font-display text-lg font-bold text-bordo-deep"
                  >
                    {avatarName}
                  </h2>
                  <p className="text-[11px] text-bordo-soft">
                    {tree?.avatar_tagline || 'Guia do inovador'}
                    {tree && nodeId !== tree.root_id ? ' · guia' : ''}
                  </p>
                </div>
              </div>
              <button
                type="button"
                className="btn-ghost !px-2 !py-1 text-sm"
                onClick={() => setOpen(false)}
                aria-label="Fechar"
              >
                ✕
              </button>
            </header>

            {/* Campo de sugestão — sempre no topo do corpo */}
            <form
              onSubmit={handleSendSugestao}
              className="border-b border-amber-100/80 bg-white/70 px-4 py-3"
            >
              <p className="mb-1.5 text-[10px] font-bold uppercase tracking-[0.14em] text-amber-800">
                Programa de Co-criação
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={sugestao}
                  onChange={(e) => setSugestao(e.target.value)}
                  disabled={sending}
                  placeholder="Tem alguma sugestão para melhorar a ferramenta?"
                  className="field-input min-h-10 flex-1 !py-2 text-sm"
                  maxLength={8000}
                />
                <button
                  type="submit"
                  disabled={sending || sugestao.trim().length < 3}
                  className="shrink-0 rounded-xl bg-gradient-to-r from-amber-500 to-rose-500 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                >
                  {sending ? '…' : 'Enviar'}
                </button>
              </div>
              <p className="mt-1.5 text-[10px] leading-relaxed text-bordo-soft">
                Se entrar no roteiro, você pode ganhar 10 planejamentos Premium (revisão da
                equipe — não é crédito automático).
              </p>
            </form>

            <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
              {loadError ? (
                <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
                  {loadError}
                </p>
              ) : null}

              {!node && !loadError ? (
                <p className="text-sm text-bordo-soft">Carregando guia…</p>
              ) : null}

              {node ? (
                <div className="rounded-2xl border border-brand-100 bg-white/90 px-3.5 py-3 shadow-sm">
                  <p className="whitespace-pre-line text-sm leading-relaxed text-bordo-deep">
                    {node.message}
                  </p>
                </div>
              ) : null}

              {upgradeHint ? (
                <p className="rounded-xl border border-brand-200 bg-brand-50 px-3 py-2 text-xs text-bordo">
                  Se o modal de planos não abriu, use <strong>Ver planos</strong> no topo da
                  tela.
                </p>
              ) : null}
            </div>

            <div className="space-y-2 border-t border-amber-100/80 bg-white/80 px-4 py-3">
              {(node?.options || []).map((opt) => (
                <button
                  key={`${opt.label}-${opt.next || ''}-${opt.href || ''}-${opt.action || ''}`}
                  type="button"
                  onClick={() => handleOption(opt)}
                  className="w-full rounded-xl border border-brand-200 bg-white px-3 py-2.5 text-left text-sm font-medium text-bordo transition hover:border-brand-400 hover:bg-brand-50"
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      {toast ? (
        <div
          role="status"
          className="fixed bottom-24 left-1/2 z-[110] w-[min(92vw,28rem)] -translate-x-1/2 animate-fade-in rounded-2xl border border-emerald-200 bg-white px-4 py-3 text-center text-sm font-medium text-emerald-900 shadow-soft sm:bottom-28"
        >
          {toast}
        </div>
      ) : null}

      <UpgradeCreditsModal
        open={showUpgrade}
        onClose={() => setShowUpgrade(false)}
      />
    </>
  )
}
