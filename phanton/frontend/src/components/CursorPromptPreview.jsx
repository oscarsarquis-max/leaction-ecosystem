import { useState } from 'react'
import { Check, ClipboardCopy } from 'lucide-react'

function tryParseJson(value) {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) return null
  try {
    return JSON.parse(trimmed)
  } catch {
    return null
  }
}

function looksLikeHtml(text) {
  if (typeof text !== 'string') return false
  const t = text.trim()
  return /^<!DOCTYPE\s+html/i.test(t) || /^<html\b/i.test(t)
}

function markdownFromObject(obj) {
  if (!obj || typeof obj !== 'object') return null
  // Preferência: entrega final; cursor_prompt só como legado
  const preferred = [
    'delivery',
    'entrega',
    'markdown',
    'documento',
    'prompt',
    'cursor_prompt',
    'prompt_markdown',
    'texto',
    'content',
  ]
  for (const key of preferred) {
    const value = obj[key]
    if (typeof value === 'string' && value.trim()) {
      // HTML não é preview de Markdown — deixa o HtmlPreview cuidar
      if (looksLikeHtml(value)) continue
      if (obj.format === 'html' && (key === 'delivery' || key === 'entrega')) continue
      const nested = tryParseJson(value)
      if (nested) {
        const fromNested = markdownFromObject(nested)
        if (fromNested) return fromNested
      }
      return value.trim()
    }
    if (value && typeof value === 'object') {
      const nested = markdownFromObject(value)
      if (nested) return nested
    }
  }
  return null
}

/** Extrai Markdown da entrega final a partir do envelope do backend. */
export function extractCursorPrompt(artifactData) {
  if (!artifactData) return null

  if (typeof artifactData === 'string') {
    const parsed = tryParseJson(artifactData)
    if (parsed) return extractCursorPrompt(parsed)
    if (looksLikeHtml(artifactData)) return null
    if (artifactData.trim().startsWith('#')) return artifactData.trim()
    return null
  }

  if (typeof artifactData !== 'object') return null

  const direct = markdownFromObject(artifactData)
  if (direct) return direct

  if (artifactData.artifact_data) {
    const nested = extractCursorPrompt(artifactData.artifact_data)
    if (nested) return nested
  }

  return null
}

// Alias semântico (UI não cita ferramenta)
export const extractDeliveryMarkdown = extractCursorPrompt

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

export default function CursorPromptPreview({
  prompt,
  title = 'Entrega final',
  editable = false,
  onChange,
}) {
  const [copied, setCopied] = useState(false)

  if (!prompt && !editable) return null

  const handleCopy = async () => {
    try {
      await copyText(prompt || '')
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
          {title}
          {editable ? ' (editável)' : ''}
        </p>
        <button
          type="button"
          onClick={handleCopy}
          className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
            copied
              ? 'border-emerald-400 bg-emerald-50 text-emerald-700'
              : 'border-indigo-300 bg-white text-indigo-800 hover:border-indigo-400 hover:bg-indigo-50'
          }`}
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5" />
              Copiado
            </>
          ) : (
            <>
              <ClipboardCopy className="h-3.5 w-3.5" />
              Copiar entrega
            </>
          )}
        </button>
      </div>
      {editable ? (
        <textarea
          value={prompt || ''}
          onChange={(e) => onChange?.(e.target.value)}
          rows={16}
          className="max-h-96 w-full resize-y overflow-auto rounded-lg border border-amber-300 bg-white p-3 font-mono text-xs leading-relaxed text-slate-800 outline-none focus:ring-2 focus:ring-amber-400"
          aria-label={title}
        />
      ) : (
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border border-indigo-100 bg-white p-3 font-mono text-xs leading-relaxed text-slate-800">
          {prompt}
        </pre>
      )}
    </div>
  )
}
