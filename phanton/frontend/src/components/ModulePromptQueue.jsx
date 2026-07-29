import { useState } from 'react'
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Circle,
  ClipboardCopy,
  Loader2,
  Lock,
} from 'lucide-react'
import CursorPromptPreview from './CursorPromptPreview'

const STATUS_UI = {
  liberado: {
    label: 'Liberado',
    className: 'border-emerald-300 bg-emerald-50 text-emerald-800',
  },
  pendente: {
    label: 'Pendente',
    className: 'border-slate-200 bg-slate-100 text-slate-600',
  },
  entregue: {
    label: 'Entregue',
    className: 'border-indigo-300 bg-indigo-50 text-indigo-800',
  },
}

async function copyText(text) {
  if (navigator?.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }
  const el = document.createElement('textarea')
  el.value = text
  el.setAttribute('readonly', '')
  el.style.position = 'fixed'
  el.style.left = '-9999px'
  document.body.appendChild(el)
  el.select()
  document.execCommand('copy')
  document.body.removeChild(el)
}

/** Bloco único para colar no IDE / log de desvios (entrega completa). */
export function formatModuleDeliveryPack(item) {
  const modulo = item?.modulo || 'modulo'
  const camada = item?.camada || 'backend'
  const escopo = item?.escopo || ''
  const deps = Array.isArray(item?.depende_de) ? item.depende_de.join(', ') : ''
  const testes = Array.isArray(item?.testes_requeridos)
    ? item.testes_requeridos.map((t) => `- ${t}`).join('\n')
    : '- (definir na implementação)'
  const prompt = (item?.prompt || '').trim()
  const today = new Date().toISOString().slice(0, 10)
  return `## Entrega — ${modulo} — ${today}

### Meta
- camada: ${camada}
- escopo: ${escopo}
- depende_de: ${deps || '(nenhuma)'}

### Prompt (copiar no IDE)
${prompt}

### Testes requeridos
${testes}

### Desvios (preencher se houver)
| ID | Tipo | O que | Incorporar em |
|----|------|-------|---------------|
| | LACUNA/CONFLITO/INFRA/CORREÇÃO | | PRD/SDD/security/prompt/só código |

### Pendências
- [ ]
`
}

export default function ModulePromptQueue({
  modules = [],
  title = 'Fila de módulos (IDE)',
  canDeliver = false,
  deliveringModulo = null,
  onDeliver,
}) {
  const [copiedModulo, setCopiedModulo] = useState(null)
  const [copiedPack, setCopiedPack] = useState(null)
  const list = Array.isArray(modules) ? modules : []

  if (!list.length) return null

  const handleCopy = async (modulo, prompt) => {
    try {
      await copyText(prompt || '')
      setCopiedModulo(modulo)
      window.setTimeout(() => setCopiedModulo(null), 1600)
    } catch {
      setCopiedModulo(null)
    }
  }

  const handleCopyPack = async (item) => {
    const modulo = item?.modulo || 'modulo'
    try {
      await copyText(formatModuleDeliveryPack(item))
      setCopiedPack(modulo)
      window.setTimeout(() => setCopiedPack(null), 1600)
    } catch {
      setCopiedPack(null)
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">{title}</p>
      <ol className="space-y-3">
        {list.map((item, idx) => {
          const status = item?.status || 'pendente'
          const ui = STATUS_UI[status] || STATUS_UI.pendente
          const modulo = item?.modulo || `modulo-${idx}`
          const liberado = status === 'liberado'
          const entregue = status === 'entregue'
          const showPrompt = liberado || entregue

          return (
            <li
              key={`${modulo}-${idx}`}
              className="rounded-xl border border-slate-200 bg-white/80 p-3 shadow-sm"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 text-left">
                  <p className="font-mono text-sm font-semibold text-slate-900">{modulo}</p>
                  {item?.camada ? (
                    <p className="mt-0.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">
                      camada: {item.camada}
                    </p>
                  ) : null}
                  {item?.escopo ? (
                    <p className="mt-0.5 text-xs text-slate-600">{item.escopo}</p>
                  ) : null}
                  {Array.isArray(item?.depende_de) && item.depende_de.length ? (
                    <p className="mt-1 text-[11px] text-slate-500">
                      depende de: {item.depende_de.join(', ')}
                    </p>
                  ) : (
                    <p className="mt-1 text-[11px] text-slate-500">sem dependências</p>
                  )}
                  {Array.isArray(item?.testes_requeridos) && item.testes_requeridos.length ? (
                    <p className="mt-1 text-[11px] font-medium text-emerald-700">
                      {item.testes_requeridos.length} teste(s) requeridos
                    </p>
                  ) : null}
                </div>
                <span
                  className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${ui.className}`}
                >
                  {entregue ? (
                    <CheckCircle2 className="h-3 w-3" />
                  ) : liberado ? (
                    <Circle className="h-3 w-3" />
                  ) : (
                    <Lock className="h-3 w-3" />
                  )}
                  {ui.label}
                </span>
              </div>

              {item?.context_consistency_warning ? (
                <div className="mt-2 flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-2.5 py-2 text-xs text-amber-950">
                  <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <span>
                    {item.context_consistency_warning}
                    {Array.isArray(item.context_forbidden_terms) &&
                    item.context_forbidden_terms.length
                      ? ` (termos: ${item.context_forbidden_terms.join(', ')})`
                      : ''}
                  </span>
                </div>
              ) : null}

              {showPrompt ? (
                <div className="mt-3 space-y-2">
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => handleCopy(modulo, item.prompt)}
                      className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-semibold transition ${
                        copiedModulo === modulo
                          ? 'border-emerald-400 bg-emerald-50 text-emerald-700'
                          : 'border-indigo-300 bg-white text-indigo-800 hover:bg-indigo-50'
                      }`}
                    >
                      {copiedModulo === modulo ? (
                        <>
                          <Check className="h-3.5 w-3.5" />
                          Copiado
                        </>
                      ) : (
                        <>
                          <ClipboardCopy className="h-3.5 w-3.5" />
                          Copiar prompt
                        </>
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleCopyPack(item)}
                      className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-semibold transition ${
                        copiedPack === modulo
                          ? 'border-emerald-400 bg-emerald-50 text-emerald-700'
                          : 'border-slate-300 bg-white text-slate-800 hover:bg-slate-50'
                      }`}
                      title="Copia prompt + testes + template de desvios"
                    >
                      {copiedPack === modulo ? (
                        <>
                          <Check className="h-3.5 w-3.5" />
                          Entrega copiada
                        </>
                      ) : (
                        <>
                          <ClipboardCopy className="h-3.5 w-3.5" />
                          Copiar entrega
                        </>
                      )}
                    </button>
                    {canDeliver && liberado ? (
                      <button
                        type="button"
                        disabled={deliveringModulo === modulo}
                        onClick={() => onDeliver?.(modulo)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-400 bg-emerald-500 px-2.5 py-1 text-xs font-semibold text-white transition hover:bg-emerald-400 disabled:opacity-60"
                      >
                        {deliveringModulo === modulo ? (
                          <>
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            Liberando…
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Marcar entregue
                          </>
                        )}
                      </button>
                    ) : null}
                  </div>
                  <CursorPromptPreview
                    prompt={item.prompt || ''}
                    title={`Prompt — ${modulo}`}
                    editable={false}
                  />
                </div>
              ) : (
                <p className="mt-2 text-xs italic text-slate-500">
                  Prompt oculto até liberar as dependências.
                </p>
              )}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
