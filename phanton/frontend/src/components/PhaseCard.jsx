import { CheckCircle2, Circle, Loader2, ShieldCheck } from 'lucide-react'
import ArtifactView from './ArtifactView'

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

export default function PhaseCard({
  phaseId,
  name,
  status = 'PENDING',
  artifactData,
  taskToken,
  isLast,
  approving,
  onApprove,
}) {
  const meta = STATUS_META[status] || STATUS_META.PENDING
  const Icon = meta.Icon
  const waiting = status === 'AWAITING_APPROVAL'

  return (
    <div className="relative flex gap-4">
      <div className="flex flex-col items-center">
        <div
          className={`flex h-11 w-11 items-center justify-center rounded-full border-2 ${meta.iconWrap}`}
        >
          <Icon className={`h-5 w-5 ${status === 'RUNNING' ? 'animate-spin' : ''}`} />
        </div>
        {!isLast && <div className="mt-1 w-0.5 flex-1 min-h-[2.5rem] bg-slate-200" />}
      </div>

      <article className={`mb-6 min-w-0 flex-1 rounded-2xl border p-5 text-left ${meta.card}`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-display text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Fase {phaseId}
            </p>
            <h3 className="font-display mt-1 truncate text-xl font-semibold text-slate-900">
              {name}
            </h3>
          </div>
          <span
            className={`inline-flex shrink-0 items-center rounded-full border px-3 py-1 text-xs font-semibold ${meta.badge}`}
          >
            {meta.label}
          </span>
        </div>

        {artifactData ? (
          <ArtifactView artifactData={artifactData} phaseId={phaseId} name={name} />
        ) : null}

        {waiting && taskToken && (
          <button
            type="button"
            disabled={approving}
            onClick={() => onApprove(taskToken)}
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
