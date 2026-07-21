import { useState } from 'react'
import { ExternalLink, Eye, EyeOff } from 'lucide-react'
import CopyableBlock from './CopyableBlock'
import FixedTextField from './FixedTextField'

export function extractHtmlCode(artifactData) {
  if (!artifactData || typeof artifactData !== 'object') return null
  if (typeof artifactData.html_code === 'string' && artifactData.html_code.trim()) {
    return artifactData.html_code
  }
  const nested = artifactData.artifact_data
  if (nested && typeof nested.html_code === 'string' && nested.html_code.trim()) {
    return nested.html_code
  }
  return null
}

export default function HtmlPreview({ htmlCode, title = 'Artefato Frontend' }) {
  const [showPreview, setShowPreview] = useState(false)

  if (!htmlCode) return null

  const openInNewTab = () => {
    const blob = new Blob([htmlCode], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener,noreferrer')
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
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
              Visualizar frontend
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
      </div>

      {showPreview && (
        <div className="overflow-hidden rounded-2xl border border-indigo-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 bg-indigo-50 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-indigo-800">
            {title}
          </div>
          <iframe
            title={title}
            srcDoc={htmlCode}
            sandbox="allow-scripts allow-forms allow-modals"
            className="h-[480px] w-full border-0 bg-white"
          />
        </div>
      )}

      <CopyableBlock
        label="Copiar HTML"
        buttonClassName="border-slate-600 bg-slate-800 text-slate-200 hover:border-slate-400 hover:bg-slate-700 hover:text-white"
        text={htmlCode}
      >
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Código HTML
        </p>
        <FixedTextField value={htmlCode} aria-label="Código HTML gerado" />
      </CopyableBlock>
    </div>
  )
}
