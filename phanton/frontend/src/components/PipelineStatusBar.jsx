import { CheckCircle2, Circle, Loader2, ShieldCheck } from 'lucide-react'
import { useEffect, useRef } from 'react'

const STEP_META = {
  PENDING: {
    label: 'Pendente',
    chip: 'border-slate-200 bg-slate-100 text-slate-600',
    Icon: Circle,
  },
  RUNNING: {
    label: 'Executando',
    chip: 'border-sky-300 bg-sky-100 text-sky-800 animate-pulse',
    Icon: Loader2,
  },
  AWAITING_APPROVAL: {
    label: 'Aguardando',
    chip: 'border-amber-400 bg-amber-100 text-amber-900',
    Icon: ShieldCheck,
  },
  APPROVED: {
    label: 'Aprovada',
    chip: 'border-emerald-300 bg-emerald-100 text-emerald-800',
    Icon: CheckCircle2,
  },
}

function phaseAnchorId(phaseId) {
  return `phase-${String(phaseId || '').replace(/[^a-zA-Z0-9_-]/g, '_')}`
}

export { phaseAnchorId }

export default function PipelineStatusBar({
  phases = [],
  runId = null,
  runStatus = null,
  bumpKey = 0,
}) {
  const barRef = useRef(null)

  // Após aprovação (bumpKey), traz a barra de volta ao topo da viewport
  useEffect(() => {
    if (!bumpKey || !barRef.current) return
    barRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [bumpKey])

  if (!phases?.length) return null

  const scrollToPhase = (phaseId) => {
    const el = document.getElementById(phaseAnchorId(phaseId))
    if (!el) return
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <section
      ref={barRef}
      className="sticky top-0 z-30 -mx-1 scroll-mt-3 rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-sm backdrop-blur"
      aria-label="Estado da execução"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-left">
          <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
            Execução
          </p>
          <h2 className="font-display mt-0.5 text-base font-semibold text-slate-950">
            Barra de estado
            {runId ? (
              <span className="ml-2 font-mono text-xs font-normal text-slate-500">
                {String(runId).slice(0, 8)}…
                {runStatus ? ` · ${runStatus}` : ''}
              </span>
            ) : null}
          </h2>
        </div>
        <p className="text-[11px] text-slate-500">
          Clique numa fase para ir ao resultado correspondente
        </p>
      </div>

      <ol className="mt-3 flex flex-wrap items-center gap-2">
        {phases.map((phase, index) => {
          const status = phase.status || 'PENDING'
          const meta = STEP_META[status] || STEP_META.PENDING
          const Icon = meta.Icon
          const spinning = status === 'RUNNING'
          return (
            <li key={phase.phase_id} className="flex items-center gap-2">
              {index > 0 ? (
                <span className="hidden h-px w-4 bg-slate-300 sm:block" aria-hidden />
              ) : null}
              <button
                type="button"
                onClick={() => scrollToPhase(phase.phase_id)}
                title={`${phase.name || phase.phase_id} — ${meta.label}`}
                className={`inline-flex max-w-[14rem] items-center gap-1.5 rounded-full border px-3 py-1.5 text-left text-xs font-semibold transition hover:brightness-95 focus:outline-none focus:ring-2 focus:ring-indigo-400 ${meta.chip}`}
              >
                <Icon className={`h-3.5 w-3.5 shrink-0 ${spinning ? 'animate-spin' : ''}`} />
                <span className="truncate">{phase.name || phase.phase_id}</span>
              </button>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
