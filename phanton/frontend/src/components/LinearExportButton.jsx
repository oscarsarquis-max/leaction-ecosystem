import { useState } from 'react'
import axios from 'axios'
import { CheckCircle2, Loader2, Send } from 'lucide-react'

/**
 * CTA de exportação do task_breakdown para o Linear.
 */
export default function LinearExportButton({
  runId,
  apiBase = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8010'),
  epicCount = 0,
  className = '',
  compact = false,
}) {
  const [isExporting, setIsExporting] = useState(false)
  const [feedback, setFeedback] = useState(null)

  if (!runId) return null

  const handleExport = async () => {
    if (isExporting) return
    setIsExporting(true)
    setFeedback(null)
    try {
      const { data } = await axios.post(`${apiBase}/api/pipeline/${runId}/export/linear`)
      const summary = data?.summary || 'Exportado com sucesso!'
      const url = data?.project?.url
      setFeedback({
        type: 'success',
        message: url ? `${summary} — ${url}` : summary,
      })
    } catch (err) {
      const detail =
        err.response?.data?.detail ||
        err.message ||
        'Falha ao exportar para o Linear'
      setFeedback({
        type: 'error',
        message: typeof detail === 'string' ? detail : JSON.stringify(detail),
      })
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className={`space-y-2 ${className}`}>
      {feedback ? (
        <div
          role="status"
          className={`flex items-start gap-2 rounded-xl border px-3 py-2.5 text-xs ${
            feedback.type === 'success'
              ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
              : 'border-red-300 bg-red-50 text-red-900'
          }`}
        >
          {feedback.type === 'success' ? (
            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          ) : null}
          <span className="break-words">{feedback.message}</span>
        </div>
      ) : null}

      <button
        type="button"
        disabled={isExporting || !runId}
        onClick={handleExport}
        className={
          compact
            ? 'inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#5E6AD2] px-4 py-2.5 font-display text-sm font-bold text-white transition hover:bg-[#4C57B8] disabled:cursor-not-allowed disabled:opacity-70 sm:w-auto'
            : 'inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#5E6AD2] px-4 py-3 font-display text-sm font-bold text-white shadow-[0_8px_24px_rgba(94,106,210,0.35)] transition hover:bg-[#4C57B8] disabled:cursor-not-allowed disabled:opacity-70'
        }
      >
        {isExporting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Exportando…
          </>
        ) : (
          <>
            <Send className="h-4 w-4" />
            Exportar para o Linear
            {epicCount > 0 ? ` (${epicCount} épicos)` : ''}
          </>
        )}
      </button>
    </div>
  )
}
