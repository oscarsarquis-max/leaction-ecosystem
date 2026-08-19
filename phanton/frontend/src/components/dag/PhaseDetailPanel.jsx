import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  ShieldCheck,
  X,
} from 'lucide-react'
import ArchitectureMermaid from '../ArchitectureMermaid'
import LinearExportButton from '../LinearExportButton'
import { extractArchitectureMermaid } from '../../lib/sddView'
import {
  extractTaskBreakdownEpics,
  isPhaseExportReady,
  unwrapArtifact,
} from '../../lib/taskBreakdown'

export { extractTaskBreakdownEpics, unwrapArtifact } from '../../lib/taskBreakdown'

const MARKDOWN_KEYS = [
  'prd_markdown',
  'sdd_markdown',
  'markdown',
  'content',
  'prompt',
  'prompt_text',
  'cursor_prompt',
  'resumo_sintese',
  'text',
]

const TYPE_TAG = {
  backend: 'border-sky-300 bg-sky-50 text-sky-800',
  frontend: 'border-violet-300 bg-violet-50 text-violet-800',
  infra: 'border-amber-300 bg-amber-50 text-amber-900',
  qa: 'border-emerald-300 bg-emerald-50 text-emerald-800',
}

function looksLikeMarkdown(text) {
  if (typeof text !== 'string') return false
  const t = text.trim()
  if (!t) return false
  if (t.startsWith('{') || t.startsWith('[')) return false
  return (
    t.includes('\n') ||
    /^#{1,6}\s/m.test(t) ||
    /^\s*[-*]\s/m.test(t) ||
    t.length > 80
  )
}

/**
 * Extrai markdown preferencial; senão null (cai para JSON).
 */
export function extractMarkdownContent(artifactData) {
  if (artifactData == null) return null
  if (typeof artifactData === 'string') {
    return looksLikeMarkdown(artifactData) ? artifactData : null
  }
  const inner = unwrapArtifact(artifactData)
  if (typeof inner === 'string') {
    return looksLikeMarkdown(inner) ? inner : null
  }
  if (!inner || typeof inner !== 'object') return null

  for (const key of MARKDOWN_KEYS) {
    const value = inner[key]
    if (typeof value === 'string' && value.trim()) {
      if (key === 'cursor_prompt' && !looksLikeMarkdown(value) && value.length < 40) {
        continue
      }
      return value
    }
  }
  return null
}

function qualityScoreFromArtifact(artifactData) {
  if (!artifactData || typeof artifactData !== 'object') return null
  if (typeof artifactData.quality_score === 'number') {
    return Math.round(artifactData.quality_score)
  }
  const nested = artifactData.meta?.quality_score
  if (typeof nested === 'number') return Math.round(nested)
  return null
}

function isTaskBreakdownCapability(capability) {
  const c = String(capability || '')
    .trim()
    .toLowerCase()
  return (
    c === 'task_breakdown' ||
    c === 'tasks_breakdown' ||
    c === 'linear_export' ||
    c === 'jira_export'
  )
}

function IssueRow({ issue, index }) {
  const [open, setOpen] = useState(false)
  const itype = String(issue?.type || 'backend').toLowerCase()
  const tagClass = TYPE_TAG[itype] || 'border-slate-300 bg-slate-50 text-slate-700'
  const micro = String(
    issue?.description_micro_prompt || issue?.description || '',
  ).trim()
  const title = String(issue?.title || `Issue ${index + 1}`).trim()

  return (
    <li
      className={`rounded-lg border border-slate-200/90 ${
        index % 2 === 0 ? 'bg-white' : 'bg-slate-50/90'
      }`}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-2 px-3 py-2.5 text-left"
      >
        {open ? (
          <ChevronDown className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
        ) : (
          <ChevronRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-slate-900">{title}</span>
            <span
              className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${tagClass}`}
            >
              {itype}
            </span>
          </div>
          {!open && micro ? (
            <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-slate-500">
              {micro}
            </p>
          ) : null}
        </div>
      </button>
      {open && micro ? (
        <div className="border-t border-slate-100 px-3 py-2.5 pl-9">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
            Micro-prompt
          </p>
          <pre className="mt-1 whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed text-slate-700">
            {micro}
          </pre>
          {Array.isArray(issue?.dependencies) && issue.dependencies.length > 0 ? (
            <p className="mt-2 text-[10px] text-slate-500">
              Depende de: {issue.dependencies.join(', ')}
            </p>
          ) : null}
        </div>
      ) : null}
    </li>
  )
}

function TaskBreakdownBoard({ epics }) {
  const issueTotal = epics.reduce(
    (n, e) => n + (Array.isArray(e.issues) ? e.issues.length : 0),
    0,
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
        <p className="text-xs font-medium text-slate-600">
          Mini-board · {epics.length} épico{epics.length === 1 ? '' : 's'} ·{' '}
          {issueTotal} issue{issueTotal === 1 ? '' : 's'}
        </p>
      </div>

      {epics.map((epic, epicIdx) => {
        const issues = Array.isArray(epic.issues) ? epic.issues : []
        return (
          <section
            key={epic.id || epic.title || epicIdx}
            className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
          >
            <header className="border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white px-4 py-3">
              <h3 className="font-display text-lg font-bold text-slate-800">
                {epic.title || `Épico ${epicIdx + 1}`}
              </h3>
              {epic.description ? (
                <p className="mt-1 text-sm leading-relaxed text-slate-600">
                  {epic.description}
                </p>
              ) : null}
            </header>
            {issues.length ? (
              <ul className="space-y-1.5 p-2.5">
                {issues.map((issue, idx) => (
                  <IssueRow
                    key={issue.id || issue.title || `${epicIdx}-${idx}`}
                    issue={issue}
                    index={idx}
                  />
                ))}
              </ul>
            ) : (
              <p className="px-4 py-3 text-xs italic text-slate-500">
                Sem issues neste épico.
              </p>
            )}
          </section>
        )
      })}
    </div>
  )
}

const STATUS_LABEL = {
  PENDING: 'Pending',
  RUNNING: 'Running',
  AWAITING_APPROVAL: 'Awaiting Approval',
  APPROVED: 'Approved',
  SUCCESS: 'Success',
  COMPLETED: 'Completed',
  FAILED: 'Failed',
  ERROR: 'Error',
}

/**
 * Slide-over lateral com artefato da fase (Markdown/JSON/task board) e ações.
 */
export default function PhaseDetailPanel({
  isOpen,
  onClose,
  phaseId,
  phaseData = null,
  artifactData = null,
  taskToken = null,
  approving = false,
  onApprove,
  immutable = false,
  runId = null,
  apiBase = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8010'),
}) {
  const status = String(phaseData?.status || 'PENDING').toUpperCase()
  const title = phaseData?.name || phaseData?.title || phaseId || 'Fase'
  const capability = phaseData?.capability || phaseData?.type || '—'
  const waiting = status === 'AWAITING_APPROVAL' && Boolean(taskToken) && !immutable
  const isBreakdown =
    isTaskBreakdownCapability(capability) ||
    isTaskBreakdownCapability(phaseId)
  const epics = useMemo(
    () => (isBreakdown ? extractTaskBreakdownEpics(artifactData) : null),
    [isBreakdown, artifactData],
  )
  const markdown = useMemo(
    () => (epics ? null : extractMarkdownContent(artifactData)),
    [epics, artifactData],
  )
  const architectureMermaid = useMemo(
    () => (epics ? null : extractArchitectureMermaid(artifactData)),
    [epics, artifactData],
  )
  const qualityScore = qualityScoreFromArtifact(artifactData)

  const canExportLinear =
    isBreakdown &&
    Boolean(runId) &&
    Boolean(epics?.length) &&
    isPhaseExportReady(status)

  useEffect(() => {
    if (!isOpen) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [isOpen, onClose, phaseId])

  if (typeof document === 'undefined') return null

  const showFooter = waiting || canExportLinear

  return createPortal(
    <>
      <button
        type="button"
        aria-label="Fechar painel"
        className={`fixed inset-0 z-40 bg-slate-950/40 transition-opacity ${
          isOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={onClose}
      />

      <aside
        role="dialog"
        aria-modal="true"
        aria-label={`Detalhe da fase ${title}`}
        className={`fixed inset-y-0 right-0 z-50 flex w-full flex-col border-l border-slate-200 bg-white shadow-2xl transition-transform duration-300 ease-out ${
          architectureMermaid && markdown
            ? 'max-w-4xl sm:w-[56%] sm:min-w-[32rem] sm:max-w-none'
            : 'max-w-xl sm:w-[38%] sm:min-w-[24rem] sm:max-w-none'
        } ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
      >
        <header className="flex shrink-0 items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
          <div className="min-w-0 text-left">
            <p className="font-mono text-[10px] uppercase tracking-wide text-slate-500">
              {phaseId}
            </p>
            <h2 className="font-display mt-0.5 truncate text-lg font-semibold text-slate-950">
              {title}
            </h2>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 font-mono text-[10px] uppercase text-slate-600">
                {capability}
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                {STATUS_LABEL[status] || status}
              </span>
              {typeof qualityScore === 'number' ? (
                <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-800">
                  Nota {qualityScore}
                </span>
              ) : null}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 p-2 text-slate-500 transition hover:bg-slate-50 hover:text-slate-800"
            aria-label="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4 text-left">
          {artifactData == null ? (
            <p className="text-sm italic text-slate-500">
              Sem artefato ainda para esta fase.
            </p>
          ) : epics ? (
            <TaskBreakdownBoard epics={epics} />
          ) : markdown ? (
            <div
              className={
                architectureMermaid
                  ? 'grid gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:items-start'
                  : ''
              }
            >
              <div className="prose prose-slate max-w-none prose-headings:font-display prose-pre:bg-slate-900 prose-pre:text-slate-100">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
              </div>
              {architectureMermaid ? (
                <ArchitectureMermaid
                  source={architectureMermaid}
                  title="Gráfico de arquitetura"
                  className="lg:sticky lg:top-0"
                />
              ) : null}
            </div>
          ) : (
            <pre className="overflow-x-auto rounded-xl border border-slate-200 bg-slate-950 p-4 text-left text-xs leading-relaxed text-slate-100">
              <code>
                {typeof artifactData === 'string'
                  ? artifactData
                  : JSON.stringify(unwrapArtifact(artifactData) ?? artifactData, null, 2)}
              </code>
            </pre>
          )}
        </div>

        {showFooter ? (
          <footer
            className={`shrink-0 space-y-3 border-t px-5 py-4 ${
              waiting
                ? 'border-amber-200 bg-amber-50/90'
                : 'border-slate-200 bg-slate-50/95'
            }`}
          >
            {waiting ? (
              <>
                <p className="text-xs text-amber-900">
                  Esta fase aguarda aprovação humana. Revise o artefato e confirme
                  para avançar o pipeline.
                </p>
                <button
                  type="button"
                  disabled={approving || typeof onApprove !== 'function'}
                  onClick={() => onApprove?.(taskToken, artifactData)}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 px-4 py-3 font-display text-sm font-bold text-white shadow-[0_0_24px_rgba(16,185,129,0.45)] transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {approving ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Aprovando…
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="h-4 w-4" />
                      Aprovar Fase
                    </>
                  )}
                </button>
              </>
            ) : null}

            {canExportLinear ? (
              <LinearExportButton
                runId={runId}
                apiBase={apiBase}
                epicCount={epics.length}
              />
            ) : null}
          </footer>
        ) : null}
      </aside>
    </>,
    document.body,
  )
}
