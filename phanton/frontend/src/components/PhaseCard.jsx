import { useEffect, useRef, useState } from 'react'
import { CheckCircle2, Circle, Loader2, RotateCcw, ShieldCheck } from 'lucide-react'
import ArtifactView from './ArtifactView'
import { phaseAnchorId } from './PipelineStatusBar'

const STATUS_META = {
  PENDING: {
    label: 'Pending',
    card: 'border-slate-200 bg-slate-50',
    badge: 'bg-slate-200 text-slate-700 border-slate-300',
    iconWrap: 'border-slate-300 bg-slate-100 text-slate-500',
    Icon: Circle,
  },
  RUNNING: {
    label: 'Running',
    card: 'border-sky-300 bg-sky-50 shadow-[0_0_0_1px_rgba(56,189,248,0.35)]',
    badge: 'bg-sky-100 text-sky-800 border-sky-300 animate-pulse',
    iconWrap: 'border-sky-400 bg-sky-100 text-sky-600 animate-pulse',
    Icon: Loader2,
  },
  AWAITING_APPROVAL: {
    label: 'Awaiting Approval',
    card: 'border-amber-400 bg-amber-50 shadow-[0_0_24px_rgba(245,158,11,0.35)]',
    badge: 'bg-amber-200 text-amber-900 border-amber-400',
    iconWrap: 'border-amber-500 bg-amber-100 text-amber-700',
    Icon: ShieldCheck,
  },
  APPROVED: {
    label: 'Approved',
    card: 'border-emerald-300 bg-emerald-50',
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    iconWrap: 'border-emerald-500 bg-emerald-100 text-emerald-700',
    Icon: CheckCircle2,
  },
}

function qualityScoreFromArtifact(artifactData) {
  if (!artifactData || typeof artifactData !== 'object') return null
  const top = artifactData.quality_score
  if (typeof top === 'number' && Number.isFinite(top)) return Math.round(top)
  const nested = artifactData.meta?.quality_score
  if (typeof nested === 'number' && Number.isFinite(nested)) return Math.round(nested)
  return null
}

function qualityBadgeClass(score) {
  if (score >= 80) return 'border-emerald-400 bg-emerald-100 text-emerald-900'
  if (score >= 50) return 'border-amber-400 bg-amber-100 text-amber-900'
  return 'border-red-400 bg-red-100 text-red-900'
}

export default function PhaseCard({
  phaseId,
  name,
  status = 'PENDING',
  artifactData,
  taskToken,
  approver = null,
  isLast,
  approving,
  onApprove,
  canDeliverModules = false,
  deliveringModulo = null,
  onDeliverModule,
  autoApproveEnabled = false,
  reopening = false,
  onReopen,
}) {
  const meta = STATUS_META[status] || STATUS_META.PENDING
  const Icon = meta.Icon
  const waiting = status === 'AWAITING_APPROVAL'
  const autoApproved =
    status === 'APPROVED' && String(approver || '').toLowerCase() === 'auto'
  const qualityScore = qualityScoreFromArtifact(artifactData)
  const lowQuality = typeof qualityScore === 'number' && qualityScore < 80
  const [draftArtifact, setDraftArtifact] = useState(artifactData)
  const draftRef = useRef(artifactData)

  useEffect(() => {
    setDraftArtifact(artifactData)
    draftRef.current = artifactData
  }, [taskToken, status, artifactData])

  const handleDraftChange = (next) => {
    draftRef.current = next
    setDraftArtifact(next)
  }

  const handleApprove = () => {
    onApprove(taskToken, draftRef.current ?? artifactData)
  }

  return (
    <div className="relative flex gap-4" id={phaseAnchorId(phaseId)}>
      <div className="flex flex-col items-center">
        <div
          className={`flex h-11 w-11 items-center justify-center rounded-full border-2 ${meta.iconWrap}`}
        >
          <Icon className={`h-5 w-5 ${status === 'RUNNING' ? 'animate-spin' : ''}`} />
        </div>
        {!isLast && <div className="mt-1 w-0.5 flex-1 min-h-[2.5rem] bg-slate-200" />}
      </div>

      <article className={`mb-6 min-w-0 flex-1 scroll-mt-28 rounded-2xl border p-5 text-left ${meta.card}`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-display text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Fase {phaseId}
            </p>
            <h3 className="font-display mt-1 truncate text-xl font-semibold text-slate-900">
              {name}
            </h3>
          </div>
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
            {typeof qualityScore === 'number' ? (
              <span
                className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${qualityBadgeClass(qualityScore)}`}
                title="Nota objetiva (fallback, retries, MAX_TOKENS, campos obrigatórios)"
              >
                Nota {qualityScore}
              </span>
            ) : null}
            <span
              className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${meta.badge}`}
            >
              {meta.label}
            </span>
          </div>
        </div>

        {waiting && autoApproveEnabled && lowQuality ? (
          <p className="mt-3 rounded-xl border border-amber-300 bg-amber-100/80 px-3 py-2 text-sm font-medium text-amber-950">
            Qualidade baixa (nota {qualityScore}) — revisão humana recomendada. Auto-aprovação
            não liberou esta fase.
          </p>
        ) : null}

        {waiting && !autoApproveEnabled && lowQuality ? (
          <p className="mt-3 rounded-xl border border-slate-200 bg-white/70 px-3 py-2 text-sm text-slate-600">
            Nota {qualityScore}: sinais de fallback/retry ou campos incompletos — revise antes de
            aprovar.
          </p>
        ) : null}

        {artifactData || draftArtifact ? (
          <ArtifactView
            artifactData={waiting ? draftArtifact ?? artifactData : artifactData}
            phaseId={phaseId}
            name={name}
            editable={waiting}
            onChange={waiting ? handleDraftChange : undefined}
            canDeliverModules={canDeliverModules}
            deliveringModulo={deliveringModulo}
            onDeliverModule={onDeliverModule}
          />
        ) : null}

        {autoApproved ? (
          <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="inline-flex flex-1 items-center gap-2 rounded-xl border border-emerald-300 bg-emerald-100/80 px-4 py-3 font-display text-sm font-semibold text-emerald-900">
              <CheckCircle2 className="h-5 w-5 shrink-0" />
              Aprovado automaticamente
              {typeof qualityScore === 'number' ? ` — nota ${qualityScore}` : ''}
            </div>
            {typeof onReopen === 'function' ? (
              <button
                type="button"
                disabled={reopening}
                onClick={() => onReopen(phaseId)}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-3 font-display text-sm font-semibold text-slate-800 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {reopening ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Reabrindo…
                  </>
                ) : (
                  <>
                    <RotateCcw className="h-4 w-4" />
                    Revisar manualmente
                  </>
                )}
              </button>
            ) : null}
          </div>
        ) : null}

        {waiting && taskToken && (
          <button
            type="button"
            disabled={approving}
            onClick={handleApprove}
            className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3.5 font-display text-base font-bold text-white shadow-[0_0_28px_rgba(16,185,129,0.55)] transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-70 sm:w-auto"
          >
            {approving ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Aprovando…
              </>
            ) : (
              <>
                <ShieldCheck className="h-5 w-5" />
                Aprovar Fase
              </>
            )}
          </button>
        )}
      </article>
    </div>
  )
}
