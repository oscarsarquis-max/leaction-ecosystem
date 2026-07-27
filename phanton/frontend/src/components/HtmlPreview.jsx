import { useEffect, useRef, useState } from 'react'
import { ExternalLink, Eye, EyeOff } from 'lucide-react'
import CopyableBlock from './CopyableBlock'
import FixedTextField from './FixedTextField'

function looksLikeHtml(text) {
  if (typeof text !== 'string') return false
  const t = text.trim()
  return /^<!DOCTYPE\s+html/i.test(t) || /^<html\b/i.test(t)
}

export function extractHtmlCode(artifactData) {
  if (!artifactData || typeof artifactData !== 'object') return null

  const candidates = [
    artifactData.html_code,
    artifactData.html,
    artifactData.format === 'html' ? artifactData.delivery : null,
    artifactData.artifact_data?.html_code,
    artifactData.artifact_data?.html,
    artifactData.artifact_data?.format === 'html'
      ? artifactData.artifact_data?.delivery
      : null,
    looksLikeHtml(artifactData.delivery) ? artifactData.delivery : null,
    looksLikeHtml(artifactData.artifact_data?.delivery)
      ? artifactData.artifact_data.delivery
      : null,
  ]

  for (const value of candidates) {
    if (typeof value === 'string' && value.trim() && looksLikeHtml(value)) {
      return value.trim()
    }
  }
  return null
}

export default function HtmlPreview({
  htmlCode,
  title = 'Entrega final',
  editable = false,
  onChange,
}) {
  const [showPreview, setShowPreview] = useState(true)
  const [blobUrl, setBlobUrl] = useState(null)
  const iframeRef = useRef(null)
  const blobUrlRef = useRef(null)

  useEffect(() => {
    if (!htmlCode || !String(htmlCode).trim()) {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current)
        blobUrlRef.current = null
      }
      setBlobUrl(null)
      return undefined
    }

    const delay = editable ? 450 : 0
    const timer = window.setTimeout(() => {
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current)
      const blob = new Blob([htmlCode], { type: 'text/html;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      blobUrlRef.current = url
      setBlobUrl(url)
    }, delay)

    return () => window.clearTimeout(timer)
  }, [htmlCode, editable])

  useEffect(() => {
    return () => {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current)
        blobUrlRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (!showPreview || !blobUrl) return undefined
    const timer = window.setTimeout(() => {
      try {
        iframeRef.current?.focus()
        iframeRef.current?.contentWindow?.focus()
      } catch {
        /* ignore */
      }
    }, 150)
    return () => window.clearTimeout(timer)
  }, [showPreview, blobUrl])

  if (!htmlCode && !editable) return null

  const openInNewTab = () => {
    if (!htmlCode) return
    const blob = new Blob([htmlCode], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const win = window.open(url, '_blank')
    if (!win) {
      URL.revokeObjectURL(url)
      return
    }
    window.setTimeout(() => URL.revokeObjectURL(url), 120_000)
  }

  return (
    <div className="mt-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setShowPreview((v) => !v)}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500"
        >
          {showPreview ? (
            <>
              <EyeOff className="h-4 w-4" />
              Ocultar visualização
            </>
          ) : (
            <>
              <Eye className="h-4 w-4" />
              Visualizar entrega
            </>
          )}
        </button>
        <button
          type="button"
          onClick={openInNewTab}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-indigo-400 hover:text-indigo-700"
        >
          <ExternalLink className="h-4 w-4" />
          Abrir em nova aba
        </button>
        {showPreview ? (
          <p className="text-xs text-slate-500">
            Clique na área da apresentação para usar teclado e botões.
          </p>
        ) : null}
      </div>

      {showPreview && blobUrl ? (
        <div className="overflow-hidden rounded-2xl border border-indigo-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 bg-indigo-50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-indigo-800">
            {title} — interativo
          </div>
          <iframe
            ref={iframeRef}
            title={title}
            src={blobUrl}
            sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups"
            className="h-[640px] w-full border-0 bg-white"
            tabIndex={0}
          />
        </div>
      ) : null}

      <CopyableBlock
        label="Copiar HTML"
        buttonClassName="border-slate-600 bg-slate-800 text-slate-200 hover:border-slate-400 hover:bg-slate-700 hover:text-white"
        text={htmlCode || ''}
      >
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Código HTML{editable ? ' (editável)' : ''}
        </p>
        <FixedTextField
          value={htmlCode || ''}
          readOnly={!editable}
          onChange={editable ? (e) => onChange?.(e.target.value) : undefined}
          aria-label="Código HTML gerado"
          className={editable ? 'h-72 border-amber-400 focus:ring-amber-400' : ''}
        />
      </CopyableBlock>
    </div>
  )
}
